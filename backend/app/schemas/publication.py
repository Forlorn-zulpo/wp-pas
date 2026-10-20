import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PublicationItemStatus, PublicationJobStatus


class PublicationJobCreate(BaseModel):
    site_id: uuid.UUID
    site_product_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class PublicationItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_product_id: uuid.UUID
    status: PublicationItemStatus
    attempt_count: int
    external_id: str | None
    error_message: str


class PublicationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    status: PublicationJobStatus
    total_items: int
    success_items: int
    failed_items: int
    created_at: datetime
    items: list[PublicationItemResponse] = Field(default_factory=list)
