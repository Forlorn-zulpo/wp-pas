import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReviewStatus


class ReviewRequest(BaseModel):
    site_product_id: uuid.UUID
    notes: str = ""


class ReviewDecision(BaseModel):
    notes: str = Field(default="", max_length=2000)


class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_product_id: uuid.UUID
    status: ReviewStatus
    notes: str
    requested_by: uuid.UUID | None
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime
