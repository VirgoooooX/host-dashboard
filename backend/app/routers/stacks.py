"""Stack router — list, start, stop, restart, update, logs."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.auth.handler import get_current_user
from app.database import get_session
from app.models import AuditLog
from app.schemas import StackOperationResponse, StackSummary
from app.services.crypto import decrypt_credentials
from app.services.dockge_client import dockge_pool, DockgeClientError
from app.services.snapshot import snapshot_manager

router = APIRouter(
    prefix="/api",
    tags=["stacks"],
    dependencies=[Depends(get_current_user)],
)

# Whitelisted actions — these map to Dockge Socket.IO events
ALLOWED_ACTIONS: dict[str, str] = {
    "start": "startStack",
    "stop": "stopStack",
    "restart": "restartStack",
    "update": "updateStack",
}


def _write_audit_log(
    session: Session,
    user: str,
    action: str,
    host_id: str,
    stack_name: str | None,
    result: str,
    detail: str | None = None,
    ip_address: str | None = None,
):
    log = AuditLog(
        user=user,
        action=action,
        host_id=host_id,
        stack_name=stack_name,
        result=result,
        detail=detail,
        ip_address=ip_address,
    )
    session.add(log)
    session.commit()


@router.get("/hosts/{host_id}/stacks", response_model=list[StackSummary])
async def list_stacks(host_id: str):
    """Return all Dockge stacks for a host, merged with container states."""
    snap = snapshot_manager.get_snapshot(host_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Host '{host_id}' not found")
    return snap.stacks


@router.get("/hosts/{host_id}/stacks/{stack_name}/logs")
async def get_stack_logs(
    host_id: str,
    stack_name: str,
    tail: int = 200,
):
    """Fetch logs for all containers belonging to a stack.

    Uses docker-socket-proxy ``/containers/{id}/logs`` for each container
    associated with the stack, then aggregates them in reverse-chronological
    order.

    Args:
        tail: Number of recent lines per container (default 200, max 5000).
    """
    if tail < 1:
        tail = 200
    if tail > 5000:
        tail = 5000

    snap = snapshot_manager.get_snapshot(host_id)
    if snap is None or snap.host_config is None:
        raise HTTPException(status_code=404, detail=f"Host '{host_id}' not found")

    # Find containers belonging to this stack
    stack_containers = [
        c
        for c in snap.containers
        if c.stack_name == stack_name and c.state == "running"
    ]
    if not stack_containers:
        return {"logs": "", "host_id": host_id, "stack": stack_name}

    # Create a proxy client for this host and fetch logs per container
    from app.services.docker_proxy import DockerProxyClient

    proxy = DockerProxyClient(snap.host_config)
    try:
        logs_parts: list[str] = []
        for c in stack_containers:
            service_label = c.service_name or c.name
            container_logs = await proxy.container_logs(c.id, tail=tail)
            if container_logs:
                logs_parts.append(
                    f"===== {service_label} ({c.id}) =====\n{container_logs}"
                )

        return {
            "logs": "\n\n".join(logs_parts),
            "host_id": host_id,
            "stack": stack_name,
        }
    finally:
        await proxy.close()


@router.post(
    "/hosts/{host_id}/stacks/{stack_name}/{action}",
    response_model=StackOperationResponse,
)
async def stack_action(
    host_id: str,
    stack_name: str,
    action: str,
    request: Request,
    session: Session = Depends(get_session),
    username: str = Depends(get_current_user),
):
    """Execute a stack operation: start, stop, restart, update.

    Only whitelisted actions are accepted.
    """
    if action not in ALLOWED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action '{action}'. Allowed: {', '.join(ALLOWED_ACTIONS.keys())}",
        )

    snap = snapshot_manager.get_snapshot(host_id)
    if snap is None or snap.host_config is None:
        _write_audit_log(
            session, username, f"stack.{action}", host_id, stack_name,
            "error", f"Host '{host_id}' not found",
            request.client.host if request.client else None,
        )
        raise HTTPException(status_code=404, detail=f"Host '{host_id}' not found")

    socket_event = ALLOWED_ACTIONS[action]

    try:
        creds = decrypt_credentials(snap.host_config.dockge_password_encrypted)
        conn = await dockge_pool.get_or_create(snap.host_config, creds["password"])
        result = await conn.stack_action(stack_name, socket_event)

        _write_audit_log(
            session, username, f"stack.{action}", host_id, stack_name,
            "success", str(result),
            request.client.host if request.client else None,
        )

        return StackOperationResponse(success=True, message=f"Stack '{stack_name}' {action} executed")
    except DockgeClientError as exc:
        _write_audit_log(
            session, username, f"stack.{action}", host_id, stack_name,
            "error", str(exc),
            request.client.host if request.client else None,
        )
        raise HTTPException(status_code=502, detail=str(exc))
