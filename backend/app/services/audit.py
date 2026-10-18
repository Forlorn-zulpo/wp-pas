import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.enums import AuditAction


async def write_audit_log(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    action: AuditAction,
    entity_type: str,
    entity_id: str = "",
    details: dict | None = None,
) -> None:
    """Appends an audit entry in the same transaction as the caller's other
    writes. Does not commit — the caller controls the transaction boundary
    so the audit entry and the data change succeed or fail together."""
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )
