import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import AssetStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Asset(UUIDPKMixin, TimestampMixin, Base):
    """An uploaded/collected image (or other media) attached to a Product.
    The original is always preserved; AI/derived versions are tracked
    separately in `derived_from_id` + `processing_meta` once Phase 5 adds
    image-processing jobs, instead of overwriting this row."""

    __tablename__ = "assets"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    content_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_primary: Mapped[bool] = mapped_column(nullable=False, default=False)
    status: Mapped[AssetStatus] = mapped_column(default=AssetStatus.UPLOADED, nullable=False)

    derived_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    processing_meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    product: Mapped["Product"] = relationship(back_populates="assets")  # noqa: F821
