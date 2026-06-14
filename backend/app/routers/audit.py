"""Audit log router — view recent operations."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, desc

from app.auth.handler import get_current_user
from app.database import get_session
from app.models import AuditLog
from app.schemas import AuditLogEntry

router = APIRouter(
    prefix="/api",
    tags=["audit"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/audit-logs", response_model=list[AuditLogEntry])
async def list_audit_logs(
    limit: int = Query(default=50, le=200, ge=1),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    """Return recent audit log entries, newest first."""
    stmt = (
        select(AuditLog)
        .order_by(desc(AuditLog.timestamp))
        .offset(offset)
        .limit(limit)
    )
    logs = session.exec(stmt).all()
    return [
        AuditLogEntry(
            id=log.id,
            timestamp=log.timestamp,
            user=log.user,
            action=log.action,
            host_id=log.host_id,
            stack_name=log.stack_name,
            result=log.result,
            detail=log.detail,
            ip_address=log.ip_address,
        )
        for log in logs
    ]
