import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SitePlatform, SiteProductStatus, SiteStatus


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    platform: SitePlatform
    base_url: str = Field(min_length=1, max_length=1000)
    credentials: dict = Field(default_factory=dict)


class SiteUpdate(BaseModel):
    version: int
    name: str | None = Field(default=None, min_length=1, max_length=255)
    base_url: str | None = Field(default=None, min_length=1, max_length=1000)
    status: SiteStatus | None = None
    # Omit entirely to leave credentials untouched; pass {} explicitly to clear them.
    credentials: dict | None = None


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    platform: SitePlatform
    base_url: str
    status: SiteStatus
    has_credentials: bool
    capabilities: dict
    last_connection_test_at: datetime | None
    last_connection_test_ok: bool | None
    version: int
    created_at: datetime


class ConnectionTestResult(BaseModel):
    ok: bool
    message: str
    tested_at: datetime


class SiteProductCreate(BaseModel):
    product_id: uuid.UUID
    site_id: uuid.UUID


class SiteProductOverrideUpdate(BaseModel):
    """Every field null/omitted means "clear the override, inherit from the
    internal product again" — there is no separate "unset" sentinel because
    a site-level override has no meaningful difference between absent and
    explicitly not customized."""

    title: str | None = None
    description: str | None = None
    price: Decimal | None = None
    category: str | None = None
    tags: list[str] | None = None
    asset_ids: list[uuid.UUID] | None = None


class SiteProductOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str | None
    description: str | None
    price: Decimal | None
    category: str | None
    tags: list
    asset_ids: list


class SiteProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    site_id: uuid.UUID
    status: SiteProductStatus
    version: int
    created_at: datetime
    override: SiteProductOverrideResponse | None = None


class PublicationPreviewResponse(BaseModel):
    """The merged view of internal Product fields + this site's overrides —
    exactly what Phase 4 would send to the remote platform. Computed on
    read, never stored, so it can never drift from the current data."""

    site_product_id: uuid.UUID
    product_id: uuid.UUID
    site_id: uuid.UUID
    title: str
    description: str
    price: Decimal
    category: str
    tags: list
    asset_ids: list[uuid.UUID]
    overridden_fields: list[str]
