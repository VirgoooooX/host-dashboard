"""Host router — overview, Docker info, metrics."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.handler import get_current_user
from app.schemas import DockerInfo, DockerDiskUsage, HostMetrics, HostListResponse
from app.services.snapshot import snapshot_manager

router = APIRouter(prefix="/api", tags=["hosts"], dependencies=[Depends(get_current_user)])


@router.get("/hosts", response_model=HostListResponse)
async def list_hosts():
    """Return a summary of all configured hosts with live status and metrics."""
    snapshots = snapshot_manager.list_snapshots()
    summaries = [snapshot_manager.build_host_summary(s) for s in snapshots]
    return HostListResponse(hosts=summaries)


@router.get("/hosts/{host_id}/docker", response_model=dict)
async def host_docker_info(host_id: str):
    """Return Docker /info and /system/df for a specific host."""
    snap = snapshot_manager.get_snapshot(host_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Host '{host_id}' not found")

    return {
        "info": snap.docker_info.model_dump() if snap.docker_info else None,
        "disk_usage": snap.docker_disk.model_dump() if snap.docker_disk else None,
        "status": snap.status,
    }


@router.get("/hosts/{host_id}/metrics", response_model=dict)
async def host_metrics(host_id: str):
    """Return host metrics from the host-metrics exporter."""
    snap = snapshot_manager.get_snapshot(host_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Host '{host_id}' not found")

    return {
        "metrics": snap.metrics.model_dump() if snap.metrics else None,
        "updated": snap.metrics_updated,
        "status": snap.status,
    }
