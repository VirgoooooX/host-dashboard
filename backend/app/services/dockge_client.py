"""Dockge Socket.IO client — connection pool with agent proxy protocol.

Maintains one socket.IO connection per configured host. All operations go
through Dockge's agent proxy layer: the browser-style socket emits an
``agent(endpoint, eventName, ...args)`` event, which the Dockge server
forwards to the backend agent socket where the actual Docker operation runs.

Key protocol details (from Dockge source at github.com/louislam/dockge):
  - Login returns ``{ ok: true, token: ... }`` (NOT ``{ status: "ok" }``).
  - After login, the server emits an ``agentList`` event listing available agents.
  - All stack operations go through ``agent(endpoint, event, ...args)``.
  - Agent handlers receive positional args (e.g. ``startStack(stackName, callback)``),
    NOT dict-wrapped arguments.
  - ``requestStackList`` returns data via a separate ``stackList`` event on the
    agent socket, which the proxy forwards back to the client socket.

Whitelisted write actions (only these are accepted):
  - startStack, stopStack, restartStack, updateStack

Events NOT whitelisted (will be rejected):
  - deleteStack, deployStack, saveStack, startService, stopService, etc.
"""

import asyncio
import logging
from typing import Any, Optional

import socketio

from app.models import HostConfig

logger = logging.getLogger(__name__)

# Actions allowed to be dispatched via the agent proxy
ALLOWED_ACTIONS: set[str] = {
    "startStack",
    "stopStack",
    "restartStack",
    "updateStack",
}

# Read-only events allowed through the agent proxy (checked in _agent_call)
READ_EVENTS: set[str] = {
    "requestStackList",
    "getStack",
    "serviceStatusList",
}


class DockgeClientError(Exception):
    """Raised on Dockge communication failures."""


class DockgeConnection:
    """A single Socket.IO connection to one Dockge instance."""

    def __init__(self, config: HostConfig, password: str):
        self._host_id = config.host_id
        self._url = config.dockge_url.rstrip("/")
        self._username = config.dockge_username
        self._password = password
        self._endpoint: str = ""
        self._sio: Optional[socketio.AsyncClient] = None
        self._connected: bool = False
        self._lock = asyncio.Lock()

    # ── Lifecycle ─────────────────────────────────────────────────

    async def connect(self) -> None:
        """Establish Socket.IO, authenticate, discover endpoint."""
        if self._connected:
            return
        async with self._lock:
            if self._connected:
                return

            self._sio = socketio.AsyncClient()
            self._sio.on("connect", self._on_connect)
            self._sio.on("disconnect", self._on_disconnect)
            self._sio.on("connect_error", self._on_connect_error)

            try:
                await self._sio.connect(
                    self._url,
                    socketio_path="/socket.io",
                    transports=["websocket", "polling"],
                    wait_timeout=10,
                )
            except Exception as exc:
                self._cleanup()
                raise DockgeClientError(
                    f"Failed to connect to Dockge at {self._url}: {exc}"
                )

            # Authenticate — Dockge returns { ok: true, token: "..." }
            try:
                auth_result = await self._sio.call(
                    "login",
                    {"username": self._username, "password": self._password},
                    timeout=15,
                )
                if not auth_result or not auth_result.get("ok"):
                    reason = (
                        auth_result.get("msg", "unknown")
                        if auth_result
                        else "no response"
                    )
                    self._cleanup()
                    raise DockgeClientError(
                        f"Dockge authentication failed for {self._host_id}: {reason}"
                    )
            except socketio.exceptions.TimeoutError:
                self._cleanup()
                raise DockgeClientError(
                    f"Dockge login timed out for {self._host_id}"
                )

            # v1 connects to each Dockge instance directly.  In Dockge's agent
            # proxy handler, an empty endpoint means "call the local agent".
            # Do not auto-pick a remote agent from agentList here; multi-agent
            # fan-out should be explicit in host config in a later version.
            self._endpoint = ""

            logger.info(
                "Dockge %s: connected, endpoint=%r",
                self._host_id,
                self._endpoint or "<default>",
            )
            self._connected = True

    async def disconnect(self) -> None:
        if self._sio and self._connected:
            await self._sio.disconnect()
        self._cleanup()

    def _cleanup(self) -> None:
        self._connected = False
        self._sio = None
        self._endpoint = ""

    async def is_connected(self) -> bool:
        return self._connected and self._sio is not None and self._sio.connected

    # ── Agent proxy calls ─────────────────────────────────────────

    async def _agent_call(self, event: str, *args: Any, timeout: int = 30) -> Any:
        """Emit via the agent proxy and return the ack response.

        For events that return data through the Socket.IO ack/callback
        mechanism (e.g. ``getStack``, ``startStack``).

        The proxy receives ``agent(endpoint, event, *args)``, forwards
        ``event(*args)`` to the agent socket, and the ack returns the result.
        """
        if not self._connected or not self._sio:
            raise DockgeClientError(f"Dockge {self._host_id}: not connected")

        if event not in READ_EVENTS and event not in ALLOWED_ACTIONS:
            raise DockgeClientError(
                f"Event '{event}' is not allowed. "
                f"Read: {sorted(READ_EVENTS)} | Write: {sorted(ALLOWED_ACTIONS)}"
            )

        payload = (self._endpoint, event) + args

        try:
            result = await self._sio.call("agent", payload, timeout=timeout)
            # Dockge returns ``False`` on agent side error
            if result is False or result is None:
                raise DockgeClientError(
                    f"Dockge {self._host_id}: agent returned false for {event}"
                )
            return result
        except socketio.exceptions.TimeoutError:
            raise DockgeClientError(
                f"Dockge {self._host_id}: {event} timed out after {timeout}s"
            )
        except DockgeClientError:
            raise
        except Exception as exc:
            raise DockgeClientError(
                f"Dockge {self._host_id}: {event} failed: {exc}"
            )

    async def _agent_emit(self, event: str, *args: Any) -> None:
        """Emit via the agent proxy without waiting for an ack.

        For events whose result comes as a separate event
        (e.g. ``requestStackList`` → ``stackList``).
        """
        if not self._connected or not self._sio:
            raise DockgeClientError(f"Dockge {self._host_id}: not connected")

        if event not in READ_EVENTS:
            raise DockgeClientError(
                f"Event '{event}' is not in read whitelist: {sorted(READ_EVENTS)}"
            )

        payload = (self._endpoint, event) + args
        try:
            await self._sio.emit("agent", payload)
        except Exception as exc:
            raise DockgeClientError(
                f"Dockge {self._host_id}: {event} emit failed: {exc}"
            )

    # ── Public API ─────────────────────────────────────────────────

    async def list_stacks(self) -> list[dict]:
        """Return all stacks from Dockge.

        Protocol: ``requestStackList(callback)`` — the ack carries no data.
        The result arrives via the ``stackList`` event forwarded from the
        agent socket.
        """
        future: "asyncio.Future[list[dict]]" = (
            asyncio.get_running_loop().create_future()
        )

        def normalize_stack_list(data: Any) -> list[dict]:
            """Normalize Dockge's stackList payload to a list of stack dicts."""
            if not isinstance(data, dict):
                return data if isinstance(data, list) else []

            raw_stacks = (
                data.get("stackList")
                or data.get("stacks")
                or data.get("data")
                or []
            )

            if isinstance(raw_stacks, dict):
                normalized: list[dict] = []
                for stack_name, stack_data in raw_stacks.items():
                    if isinstance(stack_data, dict):
                        stack = dict(stack_data)
                        stack.setdefault("name", stack_name)
                        normalized.append(stack)
                    else:
                        normalized.append({"name": stack_name, "status": stack_data})
                return normalized

            return raw_stacks if isinstance(raw_stacks, list) else []

        def on_agent_event(event_name: Any, *args: Any) -> None:
            if future.done():
                return
            if event_name != "stackList":
                return
            data = args[0] if args else {}
            future.set_result(normalize_stack_list(data))

        self._sio.on("agent", on_agent_event)

        try:
            # requestStackList itself acknowledges only that refresh was
            # requested; the actual stack data arrives as agent("stackList", ...).
            await self._agent_call("requestStackList", timeout=10)
            return await asyncio.wait_for(future, timeout=30)
        except asyncio.TimeoutError:
            raise DockgeClientError(
                f"Dockge {self._host_id}: requestStackList timed out (no agent stackList event)"
            )

    async def get_stack(self, name: str) -> Optional[dict]:
        """Get a single stack's details.

        Agent handler: ``getStack(stackName, callback)``.
        """
        return await self._agent_call("getStack", name, timeout=30)

    async def service_status(self, name: str) -> list[dict]:
        """Get service statuses for a stack.

        Agent handler: ``serviceStatusList(stackName, callback)``.
        """
        result = await self._agent_call("serviceStatusList", name, timeout=30)
        if isinstance(result, dict):
            statuses = (
                result.get("serviceStatusList")
                or result.get("services")
                or result.get("data")
                or []
            )
            if isinstance(statuses, dict):
                return [
                    {
                        "name": service_name,
                        "state": status,
                        "status": str(status),
                    }
                    for service_name, status in statuses.items()
                ]
            return statuses if isinstance(statuses, list) else []
        if isinstance(result, list):
            return result
        return []

    async def stack_action(self, name: str, action: str) -> dict:
        """Execute a whitelisted action on a stack.

        Agent handlers: ``startStack(stackName, callback)``,
        ``stopStack(stackName, callback)``, etc.

        Raises:
            DockgeClientError if action is not in ALLOWED_ACTIONS.
        """
        if action not in ALLOWED_ACTIONS:
            raise DockgeClientError(
                f"Action '{action}' is not allowed. "
                f"Allowed: {sorted(ALLOWED_ACTIONS)}"
            )

        result = await self._agent_call(action, name, timeout=60)
        if isinstance(result, dict):
            return result
        return {"result": result}

    async def get_logs(self, name: str, tail: int = 200) -> str:
        """Fetch stack logs via Docker proxy container logs.

        v1 uses the docker-socket-proxy container logs endpoint instead of
        Dockge's socket events, since ``stackLogs`` is not in the agent
        handler and per-container logs from the proxy are more reliable.

        The caller should use the Docker proxy client to fetch logs directly
        via ``/containers/<id>/logs``. This method is kept for compatibility
        and returns a placeholder.
        """
        logger.warning(
            "Dockge get_logs is not available in v1; use docker-proxy container logs instead"
        )
        return "[Logs: use container-level log endpoint via docker proxy]"

    # ── Socket.IO event handlers ───────────────────────────────────

    def _on_connect(self) -> None:
        logger.debug("Dockge %s socket connected", self._host_id)

    def _on_disconnect(self) -> None:
        self._connected = False
        logger.warning("Dockge %s socket disconnected", self._host_id)

    def _on_connect_error(self, data: Any) -> None:
        logger.error(
            "Dockge %s socket connect error: %s", self._host_id, data
        )


class DockgePool:
    """Manages multiple DockgeConnection instances, one per host."""

    def __init__(self):
        self._connections: dict[str, DockgeConnection] = {}

    async def get_or_create(
        self, config: HostConfig, password: str
    ) -> DockgeConnection:
        conn = self._connections.get(config.host_id)
        if conn is None:
            conn = DockgeConnection(config, password)
            self._connections[config.host_id] = conn
        if not await conn.is_connected():
            await conn.connect()
        return conn

    async def remove(self, host_id: str) -> None:
        conn = self._connections.pop(host_id, None)
        if conn:
            await conn.disconnect()

    async def disconnect_all(self) -> None:
        for conn in self._connections.values():
            await conn.disconnect()
        self._connections.clear()


# Singleton
dockge_pool = DockgePool()
