import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import PublicationItemStatus, PublicationJobStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin


class PublicationJob(UUIDPKMixin, TimestampMixin, Base):
    """A batch publish request against one site. The database row (not
    Redis/Celery) is the source of truth for status — Celery, once wired up
    in place of the current synchronous processing, only drives execution."""

    __tablename__ = "publication_jobs"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[PublicationJobStatus] = mapped_column(
        default=PublicationJobStatus.PENDING, nullable=False, index=True
    )
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    items: Mapped[list["PublicationItem"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class PublicationItem(UUIDPKMixin, TimestampMixin, Base):
    """One (site_product, attempted operation) within a job. Kept as its own
    row — not just a job-level counter — so a partial failure is visible
    and retryable per item, per the project's reliability requirements
    (a failure on one product must never roll back another's success)."""

    __tablename__ = "publication_items"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publication_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("site_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[PublicationItemStatus] = mapped_column(
        default=PublicationItemStatus.PENDING, nullable=False, index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")

    job: Mapped["PublicationJob"] = relationship(back_populates="items")
