import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AIProviderType, AITaskType


class AIProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider_type: AIProviderType
    base_url: str = ""
    api_key: str = ""


class AIProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    provider_type: AIProviderType
    base_url: str
    has_api_key: bool
    is_active: bool
    version: int
    created_at: datetime


class AIModelCreate(BaseModel):
    provider_id: uuid.UUID
    model_id: str = Field(min_length=1, max_length=255)
    display_name: str = ""
    supports_vision: bool = False
    supports_image_generation: bool = False
    input_cost_per_1k_tokens: Decimal | None = None
    output_cost_per_1k_tokens: Decimal | None = None


class AIModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_id: uuid.UUID
    model_id: str
    display_name: str
    supports_vision: bool
    supports_image_generation: bool
    input_cost_per_1k_tokens: Decimal | None
    output_cost_per_1k_tokens: Decimal | None
    is_active: bool
    version: int


class AITaskPolicyCreate(BaseModel):
    task_type: AITaskType
    model_id: uuid.UUID
    prompt_template: str = ""
    max_tokens: int = Field(default=1024, ge=1, le=32000)


class AITaskPolicyUpdate(BaseModel):
    version: int
    model_id: uuid.UUID | None = None
    prompt_template: str | None = None
    max_tokens: int | None = Field(default=None, ge=1, le=32000)
    is_active: bool | None = None


class AITaskPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_type: AITaskType
    model_id: uuid.UUID
    prompt_template: str
    max_tokens: int
    is_active: bool
    version: int


class AIUsageSummary(BaseModel):
    task_type: AITaskType
    call_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: Decimal
