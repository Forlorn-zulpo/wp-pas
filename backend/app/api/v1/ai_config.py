import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_credentials
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.ai import AIModel, AIProvider, AITaskPolicy, AIUsageLog
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.schemas.ai import (
    AIModelCreate,
    AIModelResponse,
    AIProviderCreate,
    AIProviderResponse,
    AITaskPolicyCreate,
    AITaskPolicyResponse,
    AITaskPolicyUpdate,
    AIUsageSummary,
)
from app.services.audit import write_audit_log

providers_router = APIRouter(prefix="/ai/providers", tags=["ai"])
models_router = APIRouter(prefix="/ai/models", tags=["ai"])
policies_router = APIRouter(prefix="/ai/task-policies", tags=["ai"])
usage_router = APIRouter(prefix="/ai/usage", tags=["ai"])


def _provider_response(p: AIProvider) -> AIProviderResponse:
    return AIProviderResponse(
        id=p.id, name=p.name, provider_type=p.provider_type, base_url=p.base_url,
        has_api_key=bool(p.encrypted_api_key), is_active=p.is_active, version=p.version,
        created_at=p.created_at,
    )


@providers_router.get("", response_model=list[AIProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    rows = (await db.execute(select(AIProvider))).scalars().all()
    return [_provider_response(p) for p in rows]


@providers_router.post("", response_model=AIProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: AIProviderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    provider = AIProvider(
        name=payload.name, provider_type=payload.provider_type, base_url=payload.base_url,
        encrypted_api_key=encrypt_credentials({"api_key": payload.api_key}) if payload.api_key else None,
    )
    db.add(provider)
    await write_audit_log(db, user_id=user.id, action=AuditAction.CREATE, entity_type="ai_provider")
    await db.commit()
    await db.refresh(provider)
    return _provider_response(provider)


@models_router.get("", response_model=list[AIModelResponse])
async def list_models(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    rows = (await db.execute(select(AIModel))).scalars().all()
    return list(rows)


@models_router.post("", response_model=AIModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    payload: AIModelCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    provider = (
        await db.execute(select(AIProvider.id).where(AIProvider.id == payload.provider_id))
    ).scalar_one_or_none()
    if provider is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="AI 服务商不存在")

    dup = (
        await db.execute(
            select(AIModel.id).where(
                AIModel.provider_id == payload.provider_id, AIModel.model_id == payload.model_id
            )
        )
    ).first()
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="该服务商下已存在相同 model_id")

    model = AIModel(**payload.model_dump())
    db.add(model)
    await write_audit_log(db, user_id=user.id, action=AuditAction.CREATE, entity_type="ai_model")
    await db.commit()
    await db.refresh(model)
    return model


@policies_router.get("", response_model=list[AITaskPolicyResponse])
async def list_task_policies(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    rows = (await db.execute(select(AITaskPolicy))).scalars().all()
    return list(rows)


@policies_router.post("", response_model=AITaskPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_task_policy(
    payload: AITaskPolicyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    model = (
        await db.execute(select(AIModel).where(AIModel.id == payload.model_id))
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="AI 模型不存在")
    if payload.task_type == "image_generation" and not model.supports_image_generation:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="该模型未声明支持图片生成能力")
    if payload.task_type in ("image_analysis", "product_recognition") and not model.supports_vision:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="该模型未声明支持视觉识别能力")

    existing = (
        await db.execute(select(AITaskPolicy).where(AITaskPolicy.task_type == payload.task_type))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="该任务类型已有策略,请改用 PATCH 更新")

    policy = AITaskPolicy(**payload.model_dump())
    db.add(policy)
    await write_audit_log(db, user_id=user.id, action=AuditAction.CREATE, entity_type="ai_task_policy")
    await db.commit()
    await db.refresh(policy)
    return policy


@policies_router.patch("/{policy_id}", response_model=AITaskPolicyResponse)
async def update_task_policy(
    policy_id: uuid.UUID,
    payload: AITaskPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    policy = (
        await db.execute(select(AITaskPolicy).where(AITaskPolicy.id == policy_id))
    ).scalar_one_or_none()
    if policy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="任务策略不存在")
    if policy.version != payload.version:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="数据已被其他人修改,请刷新后重试")

    for field, value in payload.model_dump(exclude={"version"}, exclude_unset=True).items():
        setattr(policy, field, value)

    await write_audit_log(db, user_id=user.id, action=AuditAction.UPDATE, entity_type="ai_task_policy",
                           entity_id=str(policy.id))
    await db.commit()
    await db.refresh(policy)
    return policy


@usage_router.get("/summary", response_model=list[AIUsageSummary])
async def usage_summary(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    stmt = select(
        AIUsageLog.task_type,
        func.count().label("call_count"),
        func.coalesce(func.sum(AIUsageLog.input_tokens), 0).label("total_input_tokens"),
        func.coalesce(func.sum(AIUsageLog.output_tokens), 0).label("total_output_tokens"),
        func.coalesce(func.sum(AIUsageLog.estimated_cost), 0).label("total_cost"),
    ).group_by(AIUsageLog.task_type)
    rows = (await db.execute(stmt)).all()
    return [
        AIUsageSummary(
            task_type=r.task_type, call_count=r.call_count, total_input_tokens=r.total_input_tokens,
            total_output_tokens=r.total_output_tokens, total_cost=r.total_cost,
        )
        for r in rows
    ]
