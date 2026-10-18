from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import SitePlatform, SiteStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin, VersionedMixin


class Site(UUIDPKMixin, TimestampMixin, VersionedMixin, Base):
    """One real, operating storefront. Never holds product content directly —
    product data for this site lives in SiteProduct/SiteProductOverride so a
    site row only describes *how to connect*, not what is published there."""

    __tablename__ = "sites"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[SitePlatform] = mapped_column(nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[SiteStatus] = mapped_column(default=SiteStatus.ACTIVE, nullable=False)

    # Fernet-encrypted JSON blob (api keys, consumer secret, app password —
    # shape depends on `platform`). Never serialized back to the frontend;
    # the API only ever returns whether credentials are configured.
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Populated by a connection test / capability probe (Phase 4): which
    # operations this site's credentials and API version actually support.
    capabilities: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    last_connection_test_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_connection_test_ok: Mapped[bool | None] = mapped_column(nullable=True)
