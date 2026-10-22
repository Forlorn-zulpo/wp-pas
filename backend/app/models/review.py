import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import ReviewStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ReviewItem(UUIDPKMixin, TimestampMixin, Base):
    """A review request for one SiteProduct. Publishing a SiteProduct that
    has an open (pending) review is blocked by the publish endpoint — see
    app/api/v1/publications.py — enforcing "审核与自动发布" as a real gate
    rather than a UI-only suggestion."""

    __tablename__ = "review_items"

    site_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("site_products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ReviewStatus] = mapped_column(default=ReviewStatus.PENDING, nullable=False, index=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
