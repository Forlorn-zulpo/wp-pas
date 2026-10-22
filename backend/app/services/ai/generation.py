import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_credentials
from app.models.ai import AIModel, AIProvider, AITaskPolicy, AIUsageLog
from app.models.enums import AITaskType
from app.models.product import Product
from app.services.ai.anthropic_client import AnthropicClient
from app.services.ai.base import AIClientError
from app.services.ai.openai_compatible_client import DEFAULT_BASE_URLS, OpenAICompatibleClient


class GenerationError(Exception):
    pass


def _build_client(provider, model):
    """Picks the right HTTP client for the provider's API shape. Anthropic
    uses the Messages API; everything else here speaks the OpenAI-compatible
    Chat Completions shape (DeepSeek, OPENAI, and OPENAI_COMPATIBLE for
    self-hosted/local models all fit this one client)."""
    api_key = decrypt_credentials(provider.encrypted_api_key)["api_key"]
    provider_type = provider.provider_type.value

    if provider_type == "anthropic":
        return AnthropicClient(
            api_key=api_key, model=model.model_id, base_url=provider.base_url or "https://api.anthropic.com"
        )
    if provider_type in ("deepseek", "openai", "openai_compatible"):
        base_url = provider.base_url or DEFAULT_BASE_URLS.get(provider_type, "")
        if not base_url:
            raise GenerationError(f"服务商 '{provider_type}' 未配置 base_url,且没有默认值")
        return OpenAICompatibleClient(api_key=api_key, model=model.model_id, base_url=base_url)

    raise GenerationError(f"暂不支持的服务商类型: {provider_type}")


async def generate_product_title(db: AsyncSession, product: Product) -> str:
    """Looks up the active task policy for TITLE_GENERATION, calls the
    configured model, logs usage/cost, and returns the generated title.
    Does NOT write it back to the product — the caller decides whether to
    apply it, matching the project's requirement that AI output goes
    through deterministic rules / human review rather than writing itself
    straight into the catalog."""
    policy = (
        await db.execute(
            select(AITaskPolicy).where(
                AITaskPolicy.task_type == AITaskType.TITLE_GENERATION, AITaskPolicy.is_active.is_(True)
            )
        )
    ).scalar_one_or_none()
    if policy is None:
        raise GenerationError("未配置标题生成的 AI 任务策略")

    model = (await db.execute(select(AIModel).where(AIModel.id == policy.model_id))).scalar_one_or_none()
    if model is None or not model.is_active:
        raise GenerationError("任务策略指向的 AI 模型不存在或已停用")

    provider = (
        await db.execute(select(AIProvider).where(AIProvider.id == model.provider_id))
    ).scalar_one_or_none()
    if provider is None or not provider.is_active or not provider.encrypted_api_key:
        raise GenerationError("AI 服务商未配置或未启用")

    client = _build_client(provider, model)

    system = policy.prompt_template or (
        "You write concise, accurate e-commerce product titles in the same "
        "language as the input. Reply with only the title, no quotes, no "
        "explanation."
    )
    user_message = (
        f"商品原始信息:\n名称: {product.title}\n分类: {product.category}\n"
        f"品牌: {product.brand}\n描述: {product.description[:500]}"
    )

    log = AIUsageLog(
        created_at=datetime.now(timezone.utc), model_id=model.id, task_type=AITaskType.TITLE_GENERATION,
        product_id=product.id,
    )

    try:
        result = await client.complete(system=system, user_message=user_message, max_tokens=policy.max_tokens)
    except AIClientError as exc:
        log.status = "failed"
        log.error_message = str(exc)
        db.add(log)
        raise GenerationError(str(exc)) from exc

    log.input_tokens = result.input_tokens
    log.output_tokens = result.output_tokens
    log.duration_ms = result.duration_ms
    log.status = "success"
    if model.input_cost_per_1k_tokens is not None and model.output_cost_per_1k_tokens is not None:
        log.estimated_cost = (
            Decimal(result.input_tokens) / 1000 * model.input_cost_per_1k_tokens
            + Decimal(result.output_tokens) / 1000 * model.output_cost_per_1k_tokens
        )
    db.add(log)

    return result.text.strip()
