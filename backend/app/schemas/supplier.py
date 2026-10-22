import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CollectionMethod, SupplierStatus


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    website: str = ""
    collection_method: CollectionMethod = CollectionMethod.MANUAL
    credentials: dict = Field(default_factory=dict)
    collection_config: dict = Field(default_factory=dict)
    notes: str = ""


class SupplierUpdate(BaseModel):
    version: int
    name: str | None = Field(default=None, min_length=1, max_length=255)
    website: str | None = None
    status: SupplierStatus | None = None
    collection_method: CollectionMethod | None = None
    credentials: dict | None = None
    collection_config: dict | None = None
    notes: str | None = None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    website: str
    status: SupplierStatus
    collection_method: CollectionMethod
    has_credentials: bool
    collection_config: dict
    notes: str
    version: int
    created_at: datetime
