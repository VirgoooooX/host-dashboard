"""Snapshot aggregation and caching — the central data fusion layer.

Polls three data sources per host (Dockge, docker-socket-proxy, host-metrics)
on independent schedules and caches the merged result in-memory.

Cache tiers:
  - Metrics (exporter): 3s
  - Containers/Stacks (proxy + Dockge): 10s
  - Update checks (registry): 6h
"""

import asyncio
import logging
import time
from typing import Optional

from app.config import get_settings
from app.database import engine, Session
from app.models import HostConfig
from app.schemas import (
    ContainerDetail,
    ContainerStats,
    ContainerSummary,
    ContainerPort,
    DockerInfo,
    DockerDiskUsage,
    HostMetrics,
    HostSummary,
    StackSummary,
    StackService,
)
from app.services.crypto import decrypt_credentials
from app.services.dockge_client import dockge_pool, DockgeClientError
from app.services.docker_proxy import DockerProxyClient
from app.services.metrics_client import MetricsClient
from app.services.update_check import run_update_check

logger = logging.getLogger(__name__)


class HostSnapshot:
    """Immutable snapshot of one host's data."""

    def __init__(self):
        self.host_config: Optional[HostConfig] = None
        self.status: str = "unknown"
        self.metrics: Optional[HostMetrics] = None
        self.metrics_updated: float = 0.0
        self.docker_info: Optional[DockerInfo] = None
        self.docker_disk: Optional[DockerDiskUsage] = None
        self.containers: list[ContainerSummary] = []
        self.containers_updated: float = 0.0
        self.stacks: list[StackSummary] = []
        self.stacks_updated: float = 0.0
        self.container_stats: dict[str, ContainerStats] = {}  # container_id -> stats
        self.stats_updated: float = 0.0
        self.error_message: str = ""
        # Update check results per image, keyed by image_ref
        self.update_results: dict[str, str] = {}  # image_ref -> status (up_to_date/updatable/...)
        self.update_count: int = 0


class SnapshotManager:
    """Manages all host snapshots with tiered polling."""

    def __init__(self):
        self._snapshots: dict[str, HostSnapshot] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._tasks: list[asyncio.Task] = []

        # Clients — lazily created
        self._proxy_clients: dict[str, DockerProxyClient] = {}
        self._metrics_clients: dict[str, MetricsClient] = {}
        # Dockge connections are managed by dockge_pool

    # ── Public ─────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the polling loops."""
        if self._running:
            return
        self._running = True
        settings = get_settings()
        self._tasks = [
            asyncio.create_task(
                self._poll_loop(
                    "metrics", settings.METRICS_POLL_INTERVAL, self._refresh_metrics
                )
            ),
            asyncio.create_task(
                self._poll_loop(
                    "docker", settings.DOCKER_POLL_INTERVAL, self._refresh_docker
                )
            ),
            asyncio.create_task(
                self._poll_loop(
                    "update_checks", settings.UPDATE_CHECK_INTERVAL, self._refresh_update_checks
                )
            ),
        ]
        logger.info("SnapshotManager started with tiered polling")

    async def stop(self) -> None:
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await dockge_pool.disconnect_all()
        for c in self._proxy_clients.values():
            await c.close()
        self._proxy_clients.clear()
        self._metrics_clients.clear()
        logger.info("SnapshotManager stopped")

    def get_snapshot(self, host_id: str) -> Optional[HostSnapshot]:
        return self._snapshots.get(host_id)

    def list_snapshots(self) -> list[HostSnapshot]:
        return list(self._snapshots.values())

    async def refresh_hosts(self) -> None:
        """(Re)load host configurations from database into snapshots.

        Call this after any host config change.
        """
        with Session(engine) as session:
            hosts = session.query(HostConfig).filter(HostConfig.enabled == True).all()

        async with self._lock:
            # Remove hosts no longer configured
            configured_ids = {h.host_id for h in hosts}
            for hid in list(self._snapshots.keys()):
                if hid not in configured_ids:
                    del self._snapshots[hid]
                    self._proxy_clients.pop(hid, None)
                    self._metrics_clients.pop(hid, None)
                    await dockge_pool.remove(hid)

            # Add/update snapshots
            for h in hosts:
                if h.host_id not in self._snapshots:
                    snap = HostSnapshot()
                    snap.host_config = h
                    self._snapshots[h.host_id] = snap
                else:
                    self._snapshots[h.host_id].host_config = h

    # ── Poll helpers ───────────────────────────────────────────────

    async def _poll_loop(self, name: str, interval: int, fn) -> None:
        """Generic async poll loop."""
        while self._running:
            try:
                await self.refresh_hosts()
                await fn()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Poll loop %s error: %s", name, exc, exc_info=True)
            await asyncio.sleep(interval)

    async def _refresh_metrics(self) -> None:
        """Poll all host-metrics exporters."""
        for snap in self._snapshots.values():
            if not snap.host_config:
                continue
            if snap.host_config.host_id not in self._metrics_clients:
                self._metrics_clients[snap.host_config.host_id] = MetricsClient(
                    snap.host_config
                )
            client = self._metrics_clients[snap.host_config.host_id]
            metrics = await client.fetch()
            snap.metrics = metrics
            snap.metrics_updated = time.monotonic()

    async def _refresh_docker(self) -> None:
        """Poll all docker-socket-proxy instances (info, containers, stats)."""
        for snap in self._snapshots.values():
            if not snap.host_config:
                continue
            cfg = snap.host_config
            if cfg.host_id not in self._proxy_clients:
                self._proxy_clients[cfg.host_id] = DockerProxyClient(cfg)
            proxy = self._proxy_clients[cfg.host_id]

            try:
                # Version / Info
                ver = await proxy.version()
                info = await proxy.info()
                snap.docker_info = DockerInfo(
                    version=ver.get("Version"),
                    api_version=ver.get("ApiVersion"),
                    os=info.get("OSType"),
                    architecture=info.get("Architecture"),
                    docker_root_dir=info.get("DockerRootDir"),
                    server_version=info.get("ServerVersion"),
                    kernel_version=info.get("KernelVersion"),
                    operating_system=info.get("OperatingSystem"),
                    n_cpus=info.get("NCPU"),
                    memory_total=info.get("MemTotal"),
                    name=info.get("Name"),
                )

                # Disk usage
                df = await proxy.disk_usage()
                snap.docker_disk = DockerDiskUsage(
                    images_total=len(df.get("Images", [])),
                    images_size=sum(
                        i.get("Size", 0) for i in df.get("Images", [])
                    ),
                    containers_total=len(df.get("Containers", [])),
                    containers_size=sum(
                        c.get("SizeRw", 0) for c in df.get("Containers", [])
                    ),
                    volumes_total=len(df.get("Volumes", [])),
                    volumes_size=sum(
                        v.get("UsageData", {}).get("Size", 0)
                        for v in df.get("Volumes", [])
                    ),
                    build_cache_total=len(df.get("BuildCache", [])),
                    build_cache_size=sum(
                        b.get("Size", 0) for b in df.get("BuildCache", [])
                    ),
                )
                snap.containers_updated = time.monotonic()

                # Container list
                raw_containers = await proxy.list_containers(all=True)
                snap.containers = []
                for c in raw_containers:
                    ports = [
                        ContainerPort(
                            private_port=p.get("PrivatePort"),
                            public_port=p.get("PublicPort"),
                            ip=p.get("IP"),
                            type=p.get("Type", "tcp"),
                        )
                        for p in c.get("Ports", [])
                    ]
                    # Extract stack/service from compose labels
                    labels = c.get("Labels", {}) or {}
                    stack_name = (
                        labels.get("com.docker.compose.project")
                        or labels.get("com.dockge.stack")
                    )
                    service_name = labels.get("com.docker.compose.service")

                    snap.containers.append(
                        ContainerSummary(
                            id=c.get("Id", "")[:12],
                            name=c.get("Name", "").lstrip("/"),
                            image=c.get("Image", ""),
                            image_id=c.get("ImageID", ""),
                            state=c.get("State", "unknown"),
                            status=c.get("Status", ""),
                            created=c.get("Created", 0),
                            ports=ports,
                            labels=labels,
                            stack_name=stack_name,
                            service_name=service_name,
                        )
                    )

                # Fetch RepoDigests for each unique image
                unique_images = list({c.image for c in snap.containers if c.image})
                image_digests: dict[str, list[str]] = {}
                for img_name in unique_images:
                    try:
                        img_info = await proxy.image_inspect(img_name)
                        rd = img_info.get("RepoDigests", []) or []
                        image_digests[img_name] = rd
                    except Exception as exc:
                        logger.debug(
                            "Image inspect failed for %s/%s: %s",
                            cfg.host_id, img_name, exc,
                        )
                        image_digests[img_name] = []
                for c in snap.containers:
                    c.repo_digests = image_digests.get(c.image, [])

                # Container stats (running only)
                snap.stats_updated = time.monotonic()
                for c in snap.containers:
                    if c.state != "running":
                        continue
                    stats = await proxy.container_stats(c.id)
                    if stats is None:
                        continue
                    try:
                        cpu_delta = stats.get("cpu_stats", {}).get(
                            "cpu_usage", {}
                        ).get("total_usage", 0) - stats.get("precpu_stats", {}).get(
                            "cpu_usage", {}
                        ).get("total_usage", 0)
                        system_delta = stats.get("cpu_stats", {}).get(
                            "system_cpu_usage", 0
                        ) - stats.get("precpu_stats", {}).get(
                            "system_cpu_usage", 1
                        )
                        num_cpus = stats.get("cpu_stats", {}).get(
                            "online_cpus", 1
                        )
                        cpu_percent = 0.0
                        if system_delta > 0 and cpu_delta > 0:
                            cpu_percent = round(
                                (cpu_delta / system_delta) * num_cpus * 100.0, 1
                            )

                        mem = stats.get("memory_stats", {})
                        net = stats.get("networks", {})
                        blk = stats.get("blkio_stats", {})

                        snap.container_stats[c.id] = ContainerStats(
                            cpu_percent=cpu_percent,
                            memory_usage=mem.get("usage", 0),
                            memory_limit=mem.get("limit", 0),
                            memory_percent=round(
                                (mem.get("usage", 0) / max(mem.get("limit", 1), 1))
                                * 100,
                                1,
                            ),
                            network_rx_bytes=sum(
                                n.get("rx_bytes", 0) for n in net.values()
                            ),
                            network_tx_bytes=sum(
                                n.get("tx_bytes", 0) for n in net.values()
                            ),
                            block_read_bytes=sum(
                                e.get("value", 0)
                                for e in blk.get("io_service_bytes_recursive", [])
                                if e.get("op") == "read"
                            ),
                            block_write_bytes=sum(
                                e.get("value", 0)
                                for e in blk.get("io_service_bytes_recursive", [])
                                if e.get("op") == "write"
                            ),
                        )
                    except Exception as exc:
                        logger.debug(
                            "Stats parse error for %s/%s: %s",
                            cfg.host_id,
                            c.id,
                            exc,
                        )

                # Stacks from Dockge
                await self._refresh_stacks(snap, cfg)

                snap.status = "online"
                snap.error_message = ""

                # Trigger an initial update check after the first successful
                # docker poll that has containers.  This handles the gap where
                # the update check loop (6h) runs before containers are ready.
                if snap.containers and not hasattr(snap, "_update_triggered"):
                    snap._update_triggered = True
                    asyncio.create_task(self._refresh_update_checks_single(cfg.host_id, snap))

            except Exception as exc:
                logger.warning(
                    "Docker proxy poll failed for %s: %s", cfg.host_id, exc
                )
                snap.status = "degraded"
                snap.error_message = str(exc)

    async def _refresh_stacks(self, snap: HostSnapshot, cfg: HostConfig) -> None:
        """Fetch and merge Dockge stacks with container states."""
        try:
            # Decrypt Dockge password
            creds = decrypt_credentials(cfg.dockge_password_encrypted)
            conn = await dockge_pool.get_or_create(cfg, creds["password"])

            raw_stacks = await conn.list_stacks()
            stacks: list[StackSummary] = []
            for s in raw_stacks:
                name = s.get("name", s.get("Name", ""))
                services_raw = s.get("services", s.get("Services", [])) or []
                compose_file = s.get("composeFile", s.get("filePath"))

                svcs: list[StackService] = []
                running = 0
                for svc in services_raw:
                    state = svc.get("state", svc.get("State", "unknown"))
                    if state == "running":
                        running += 1
                    svcs.append(
                        StackService(
                            name=svc.get("name", svc.get("Name", "")),
                            container_id=svc.get("containerId"),
                            state=state,
                            status=svc.get("status", ""),
                        )
                    )

                # Overall stack status
                if not svcs:
                    overall = "unknown"
                elif running == len(svcs):
                    overall = "running"
                elif running == 0:
                    overall = "stopped"
                else:
                    overall = "partially running"

                stacks.append(
                    StackSummary(
                        name=name,
                        status=overall,
                        compose_file=compose_file,
                        service_count=len(svcs),
                        running_count=running,
                        services=svcs,
                    )
                )

            snap.stacks = stacks
            snap.stacks_updated = time.monotonic()

        except Exception as exc:
            logger.warning("Dockge refresh failed for %s: %s", cfg.host_id, exc)

    # ── Update checks ─────────────────────────────────────────────

    async def _refresh_update_checks(self) -> None:
        """Query registry digests for all container images across all hosts.

        Runs every 6 hours. Results are cached in-memory.
        """
        for snap in self._snapshots.values():
            if not snap.host_config or not snap.containers:
                continue
            host_id = snap.host_config.host_id

            # Build (image_ref, repo_digests) tuples
            image_refs: list[tuple[str, list[str]]] = []
            for c in snap.containers:
                image_refs.append((c.image, c.repo_digests))

            try:
                results = await run_update_check(host_id, image_refs)
                # Store per-image status
                updatable = 0
                snap.update_results.clear()
                for r in results:
                    snap.update_results[r.image] = r.status
                    if r.status == "updatable":
                        updatable += 1
                snap.update_count = updatable
            except Exception as exc:
                logger.warning(
                    "Update check failed for %s: %s", host_id, exc, exc_info=True
                )

    async def _refresh_update_checks_single(
        self, host_id: str, snap: HostSnapshot
    ) -> None:
        """Run a one-shot update check for a single host.

        Called after the first successful docker poll that populates containers.
        This avoids waiting for the 6h poll interval on initial startup.
        """
        if not snap.host_config or not snap.containers:
            return
        image_refs = [(c.image, c.repo_digests) for c in snap.containers]
        try:
            results = await run_update_check(host_id, image_refs)
            updatable = 0
            for r in results:
                if r.status == "updatable":
                    updatable += 1
            snap.update_count = updatable
            logger.info(
                "Initial update check for %s: %d updatable out of %d",
                host_id, updatable, len(results),
            )
        except Exception as exc:
            logger.warning(
                "Initial update check failed for %s: %s", host_id, exc
            )

    # ── Build summaries for API ────────────────────────────────────

    def build_host_summary(self, snap: HostSnapshot) -> HostSummary:
        """Build a HostSummary from a snapshot, for the /api/hosts response."""
        cfg = snap.host_config
        info = snap.docker_info
        disk = snap.docker_disk
        containers = snap.containers

        if info is None and snap.status == "degraded":
            effective_status = "degraded"
        elif snap.metrics is None and snap.status == "online":
            effective_status = "degraded"
        else:
            effective_status = snap.status

        return HostSummary(
            host_id=cfg.host_id,
            display_name=cfg.display_name or cfg.host_id,
            status=effective_status,
            metrics=snap.metrics,
            docker_version=info.version if info else None,
            api_version=info.api_version if info else None,
            os_info=info.operating_system if info else None,
            architecture=info.architecture if info else None,
            docker_root_dir=info.docker_root_dir if info else None,
            container_running=sum(1 for c in containers if c.state == "running"),
            container_stopped=sum(1 for c in containers if c.state != "running"),
            container_total=len(containers),
            image_count=disk.images_total if disk else 0,
            docker_disk_images=disk.images_size if disk else None,
            docker_disk_containers=disk.containers_size if disk else None,
            docker_disk_volumes=disk.volumes_size if disk else None,
            docker_disk_build_cache=disk.build_cache_size if disk else None,
            update_count=snap.update_count,  # From update_check background task
        )


# Singleton
snapshot_manager = SnapshotManager()
