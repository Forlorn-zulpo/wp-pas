import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CollectionJobStatus


class CollectionJobCreate(BaseModel):
    supplier_id: uuid.UUID
    target_config: dict = Field(default_factory=dict)


class CollectionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    status: CollectionJobStatus
    target_config: dict
    total_items: int
    success_items: int
    error_items: int
    errors: list
    created_at: datetime
