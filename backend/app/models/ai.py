import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.enums import AIProviderType, AITaskType
from app.models.mixins import TimestampMixin, UUIDPKMixin, VersionedMixin


class AIProvider(UUIDPKMixin, TimestampMixin, VersionedMixin, Base):
    """One configured credential set for one AI vendor. A provider can have
    several Models (e.g. one Anthropic provider with claude-haiku and
    claude-sonnet both configured) — the provider holds the API key, the
    model holds the model id and declared capabilities."""

    __tablename__ = "ai_providers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_type: Mapped[AIProviderType] = mapped_column(nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    encrypted_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    models: Mapped[list["AIModel"]] = relationship(back_populates="provider", cascade="all, delete-orphan")


class AIModel(UUIDPKMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "ai_models"
    __table_args__ = (UniqueConstraint("provider_id", "model_id", name="uq_provider_model"),)

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The vendor's own model identifier, e.g. "claude-sonnet-4-6",
    # "gpt-4o-mini" — never assumed, always explicitly configured, per the
    # project's requirement to check capabilities rather than assume them.
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    supports_vision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_image_generation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    input_cost_per_1k_tokens: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    output_cost_per_1k_tokens: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    provider: Mapped["AIProvider"] = relationship(back_populates="models")


class AITaskPolicy(UUIDPKMixin, TimestampMixin, VersionedMixin, Base):
    """Which model handles which task type. Unique per task_type: exactly
    one active policy decides, e.g., which model generates titles."""

    __tablename__ = "ai_task_policies"
    __table_args__ = (UniqueConstraint("task_type", name="uq_task_policy_per_task"),)

    task_type: Mapped[AITaskType] = mapped_column(nullable=False, index=True)
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="CASCADE"), nullable=False
    )
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=1024)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AIUsageLog(UUIDPKMixin, Base):
    """Append-only, like AuditLog — one row per AI call, for the cost and
    usage reporting the project requires."""

    __tablename__ = "ai_usage_logs"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True
    )
    task_type: Mapped[AITaskType] = mapped_column(nullable=False, index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="success")
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
