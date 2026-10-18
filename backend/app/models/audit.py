import uuid

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import AuditAction, ImportStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin


class AuditLog(UUIDPKMixin, Base):
    __tablename__ = "audit_logs"

    # No updated_at/version here: audit entries are append-only by design.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[AuditAction] = mapped_column(nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, default="", index=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class ImportJob(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "import_jobs"

    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ImportStatus] = mapped_column(default=ImportStatus.PENDING, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # List of {row, field, message} — kept bounded in the service layer so a
    # huge bad file can't blow up this column.
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
