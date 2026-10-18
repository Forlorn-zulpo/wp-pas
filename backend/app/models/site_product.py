import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import SiteProductStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin, VersionedMixin


class SiteProduct(UUIDPKMixin, TimestampMixin, VersionedMixin, Base):
    """The binding between one internal Product and one Site. Binding is
    deliberately a separate step from publishing: creating this row never
    talks to the remote site — it only means "this product is scoped to be
    managed for this site." Actual publish/unpublish happens in Phase 4 and
    changes `status` + writes an ExternalProductMapping; it never touches
    this row's sibling SiteProducts for other sites, so a failure on one
    site cannot roll back another site's already-successful publish."""

    __tablename__ = "site_products"
    __table_args__ = (UniqueConstraint("product_id", "site_id", name="uq_site_product_binding"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[SiteProductStatus] = mapped_column(
        default=SiteProductStatus.BOUND, nullable=False, index=True
    )

    override: Mapped["SiteProductOverride"] = relationship(
        back_populates="site_product", uselist=False, cascade="all, delete-orphan"
    )
    external_mapping: Mapped["ExternalProductMapping"] = relationship(
        back_populates="site_product", uselist=False, cascade="all, delete-orphan"
    )


class SiteProductOverride(UUIDPKMixin, TimestampMixin, Base):
    """Every field here is nullable and means "inherit the internal Product's
    value" when null. Setting a field here NEVER writes back to Product —
    this is the mechanism that keeps one site's customization from leaking
    into the internal record or any other site."""

    __tablename__ = "site_product_overrides"

    site_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("site_products.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Ordered list of Asset ids to use for this site instead of the
    # product's own asset order; empty means "use the product's assets".
    asset_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    site_product: Mapped["SiteProduct"] = relationship(back_populates="override")


class ExternalProductMapping(UUIDPKMixin, TimestampMixin, Base):
    """Links a SiteProduct to the remote platform's own identifiers. This is
    what Phase 4's idempotency and reconciliation logic reads before
    creating a remote product, to avoid creating duplicates after a timeout."""

    __tablename__ = "external_product_mappings"

    site_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("site_products.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_variant_ids: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_remote_status: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    site_product: Mapped["SiteProduct"] = relationship(back_populates="external_mapping")
