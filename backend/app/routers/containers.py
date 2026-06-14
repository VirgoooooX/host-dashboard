"""Container router — list containers with stats."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.handler import get_current_user
from app.schemas import ContainerDetail, ContainerSummary, ContainerStats
from app.services.snapshot import snapshot_manager

router = APIRouter(
    prefix="/api",
    tags=["containers"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/hosts/{host_id}/containers", response_model=list[ContainerSummary])
async def list_containers(host_id: str):
    """Return all containers (running + stopped) for a host."""
    snap = snapshot_manager.get_snapshot(host_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Host '{host_id}' not found")
    return snap.containers


@router.get("/hosts/{host_id}/container-stats", response_model=dict)
async def container_stats_bulk(host_id: str):
    """Return all cached container stats as ``{container_id: ContainerStats}``.

    Stats are collected during the background docker poll (every 10s).
    Only running containers have stats entries.
    """
    snap = snapshot_manager.get_snapshot(host_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Host '{host_id}' not found")

    return {
        cid: stats.model_dump()
        for cid, stats in snap.container_stats.items()
    }


@router.get("/hosts/{host_id}/containers/{container_id}", response_model=ContainerDetail)
async def container_detail(host_id: str, container_id: str):
    """Return detailed info + stats for a single container."""
    snap = snapshot_manager.get_snapshot(host_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Host '{host_id}' not found")

    container = next(
        (c for c in snap.containers if c.id.startswith(container_id)), None
    )
    if container is None:
        raise HTTPException(
            status_code=404,
            detail=f"Container '{container_id}' not found on host '{host_id}'",
        )

    stats = snap.container_stats.get(container.id)

    return ContainerDetail(
        summary=container,
        stats=stats,
    )
