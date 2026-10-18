import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProductStatus


class VariantCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    options: dict = Field(default_factory=dict)
    price_override: Decimal | None = None
    stock_quantity: int = Field(default=0, ge=0)
    barcode: str = ""


class VariantUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    options: dict | None = None
    price_override: Decimal | None = None
    stock_quantity: int | None = Field(default=None, ge=0)
    barcode: str | None = None


class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    options: dict
    price_override: Decimal | None
    stock_quantity: int
    barcode: str
    version: int


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    storage_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    width: int | None
    height: int | None
    position: int
    is_primary: bool
    status: str


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    description: str = ""
    category: str = ""
    brand: str = ""
    status: ProductStatus = ProductStatus.DRAFT
    price: Decimal = Decimal("0")
    cost_price: Decimal | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    attributes: dict = Field(default_factory=dict)
    variants: list[VariantCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """All fields optional — PATCH semantics. `version` is required so the
    service layer can enforce optimistic locking against the row the client
    last read, rejecting the update with 409 if someone else changed it."""

    version: int
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    category: str | None = None
    brand: str | None = None
    status: ProductStatus | None = None
    price: Decimal | None = None
    cost_price: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    attributes: dict | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    title: str
    description: str
    category: str
    brand: str
    status: ProductStatus
    price: Decimal
    cost_price: Decimal | None
    currency: str
    attributes: dict
    version: int
    created_at: datetime
    updated_at: datetime


class ProductDetailResponse(ProductResponse):
    variants: list[VariantResponse] = Field(default_factory=list)
    assets: list[AssetResponse] = Field(default_factory=list)


class PagedResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


class BulkUpdateRequest(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=500)
    status: ProductStatus | None = None
    category: str | None = None
    brand: str | None = None


class BulkUpdateResponse(BaseModel):
    updated_count: int
    not_found_ids: list[uuid.UUID]


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: str
    total_rows: int
    success_rows: int
    error_rows: int
    errors: list
    created_at: datetime
