import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import CollectionJobStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin


class CollectionJob(UUIDPKMixin, TimestampMixin, Base):
    """One run of collecting products from a Supplier. The actual scraper
    implementation is supplier-specific (per the project's "choose the
    right method per supplier" principle) and lives in
    app/services/collectors/<supplier-specific module>; this row only
    tracks the run's lifecycle, independent of which collection method was
    used, so the API/UI never needs to know."""

    __tablename__ = "collection_jobs"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[CollectionJobStatus] = mapped_column(
        default=CollectionJobStatus.PENDING, nullable=False, index=True
    )
    target_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
