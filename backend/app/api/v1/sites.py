import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_credentials
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import AuditAction, UserRole
from app.models.site import Site
from app.models.user import User
from app.schemas.site import ConnectionTestResult, SiteCreate, SiteResponse, SiteUpdate
from app.services.audit import write_audit_log

router = APIRouter(prefix="/sites", tags=["sites"])


def _to_response(site: Site) -> SiteResponse:
    return SiteResponse(
        id=site.id,
        name=site.name,
        platform=site.platform,
        base_url=site.base_url,
        status=site.status,
        has_credentials=bool(site.encrypted_credentials),
        capabilities=site.capabilities,
        last_connection_test_at=site.last_connection_test_at,
        last_connection_test_ok=site.last_connection_test_ok,
        version=site.version,
        created_at=site.created_at,
    )


@router.get("", response_model=list[SiteResponse])
async def list_sites(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    sites = (await db.execute(select(Site).order_by(Site.created_at.desc()))).scalars().all()
    return [_to_response(s) for s in sites]


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    payload: SiteCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    site = Site(
        name=payload.name,
        platform=payload.platform,
        base_url=payload.base_url,
        encrypted_credentials=encrypt_credentials(payload.credentials) if payload.credentials else None,
    )
    db.add(site)
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.CREATE, entity_type="site",
        details={"name": payload.name, "platform": payload.platform.value},
    )
    await db.commit()
    await db.refresh(site)
    return _to_response(site)


async def _get_site_or_404(db: AsyncSession, site_id: uuid.UUID) -> Site:
    site = (await db.execute(select(Site).where(Site.id == site_id))).scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="站点不存在")
    return site


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)
):
    return _to_response(await _get_site_or_404(db, site_id))


@router.patch("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: uuid.UUID,
    payload: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    site = await _get_site_or_404(db, site_id)
    if site.version != payload.version:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="数据已被其他人修改,请刷新后重试")

    updates = payload.model_dump(exclude={"version", "credentials"}, exclude_unset=True)
    for field, value in updates.items():
        setattr(site, field, value)

    if "credentials" in payload.model_fields_set:
        site.encrypted_credentials = (
            encrypt_credentials(payload.credentials) if payload.credentials else None
        )
        # Credentials changed — any previous connection test is no longer valid evidence.
        site.last_connection_test_ok = None
        site.last_connection_test_at = None

    await write_audit_log(
        db, user_id=user.id, action=AuditAction.UPDATE, entity_type="site", entity_id=str(site.id),
        details={"fields": list(updates.keys())},
    )
    await db.commit()
    await db.refresh(site)
    return _to_response(site)


@router.post("/{site_id}/test-connection", response_model=ConnectionTestResult)
async def test_connection(
    site_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Phase 3 scope: verifies the configured base_url is actually reachable
    over HTTPS/HTTP. Platform-specific authenticated capability detection
    (e.g. "can this WooCommerce key create products") is Phase 4 work, once
    a real connector exists to make the authenticated call."""
    site = await _get_site_or_404(db, site_id)

    ok = False
    message = ""
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as http_client:
            resp = await http_client.get(site.base_url)
        ok = resp.status_code < 500
        message = f"站点可访问,HTTP 状态码 {resp.status_code}"
    except httpx.RequestError as exc:
        message = f"无法连接站点: {exc}"

    tested_at = datetime.now(timezone.utc)
    site.last_connection_test_ok = ok
    site.last_connection_test_at = tested_at

    await write_audit_log(
        db, user_id=user.id, action=AuditAction.TEST_CONNECTION, entity_type="site",
        entity_id=str(site.id), details={"ok": ok},
    )
    await db.commit()
    return ConnectionTestResult(ok=ok, message=message, tested_at=tested_at)
