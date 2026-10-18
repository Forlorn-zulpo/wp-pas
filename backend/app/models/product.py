import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.asset import Asset  # noqa: F401  (needed for the "Asset" relationship string below)
from app.models.enums import ProductStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin, VersionedMixin


class Product(UUIDPKMixin, TimestampMixin, VersionedMixin, Base):
    """Internal, canonical product record — never written to directly by a
    site publish flow. Site-specific presentation lives in SiteProductOverride
    (added in Phase 3), so editing a site's listing never mutates this row."""

    __tablename__ = "products"
    __table_args__ = (Index("ix_products_title_trgm", "title"),)

    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(255), nullable=False, default="", index=True)
    brand: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[ProductStatus] = mapped_column(
        default=ProductStatus.DRAFT, nullable=False, index=True
    )

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")

    # Free-form attributes (e.g. material, color family) that don't warrant
    # their own column yet; kept separate from variant-level options.
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # No FK yet: the suppliers table is built in Phase 5. Column is reserved
    # now so Phase 5 only needs to add a constraint, not a migration that
    # touches every existing product row.
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="Asset.position"
    )


class ProductVariant(UUIDPKMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (Index("ix_variants_product_id", "product_id"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    # e.g. {"color": "Red", "size": "M"}
    options: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    price_override: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    stock_quantity: Mapped[int] = mapped_column(nullable=False, default=0)
    barcode: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    product: Mapped["Product"] = relationship(back_populates="variants")
