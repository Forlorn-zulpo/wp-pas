import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import AuditAction, SiteProductStatus, UserRole
from app.models.product import Product
from app.models.site import Site
from app.models.site_product import ExternalProductMapping, SiteProduct, SiteProductOverride
from app.models.user import User
from app.schemas.site import (
    PublicationPreviewResponse,
    SiteProductCreate,
    SiteProductOverrideUpdate,
    SiteProductResponse,
)
from app.services.audit import write_audit_log

router = APIRouter(tags=["site-products"])


async def _get_site_product_or_404(db: AsyncSession, site_product_id: uuid.UUID) -> SiteProduct:
    stmt = (
        select(SiteProduct)
        .where(SiteProduct.id == site_product_id)
        .options(selectinload(SiteProduct.override))
    )
    sp = (await db.execute(stmt)).scalar_one_or_none()
    if sp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="站点商品绑定不存在")
    return sp


@router.post("/site-products", response_model=SiteProductResponse, status_code=status.HTTP_201_CREATED)
async def bind_product_to_site(
    payload: SiteProductCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Binding never contacts the remote site — see SiteProduct's docstring.
    It only records that this product is now in scope for this site."""
    product = (
        await db.execute(select(Product.id).where(Product.id == payload.product_id))
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="商品不存在")
    site = (await db.execute(select(Site.id).where(Site.id == payload.site_id))).scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="站点不存在")

    existing = (
        await db.execute(
            select(SiteProduct.id).where(
                SiteProduct.product_id == payload.product_id, SiteProduct.site_id == payload.site_id
            )
        )
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="该商品已绑定到此站点")

    site_product = SiteProduct(
        product_id=payload.product_id,
        site_id=payload.site_id,
        override=SiteProductOverride(),
        external_mapping=ExternalProductMapping(),
    )
    db.add(site_product)
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.BIND, entity_type="site_product",
        details={"product_id": str(payload.product_id), "site_id": str(payload.site_id)},
    )
    await db.commit()
    await db.refresh(site_product, attribute_names=["override"])
    return site_product


@router.get("/site-products", response_model=list[SiteProductResponse])
async def list_site_products(
    product_id: uuid.UUID | None = Query(default=None),
    site_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    stmt = select(SiteProduct).options(selectinload(SiteProduct.override))
    if product_id:
        stmt = stmt.where(SiteProduct.product_id == product_id)
    if site_id:
        stmt = stmt.where(SiteProduct.site_id == site_id)
    rows = (await db.execute(stmt.order_by(SiteProduct.created_at.desc()))).scalars().all()
    return list(rows)


@router.get("/site-products/{site_product_id}", response_model=SiteProductResponse)
async def get_site_product(
    site_product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await _get_site_product_or_404(db, site_product_id)


@router.patch("/site-products/{site_product_id}/override", response_model=SiteProductResponse)
async def update_override(
    site_product_id: uuid.UUID,
    payload: SiteProductOverrideUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Writes only to SiteProductOverride — this function never touches the
    Product row, so editing one site's listing cannot leak into the
    internal product or any other site bound to it."""
    site_product = await _get_site_product_or_404(db, site_product_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "asset_ids" and value is not None:
            value = [str(v) for v in value]
        setattr(site_product.override, field, value)

    await write_audit_log(
        db, user_id=user.id, action=AuditAction.UPDATE, entity_type="site_product_override",
        entity_id=str(site_product_id), details={"fields": list(updates.keys())},
    )
    await db.commit()
    await db.refresh(site_product, attribute_names=["override"])
    return site_product


@router.delete("/site-products/{site_product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unbind_product(
    site_product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    site_product = await _get_site_product_or_404(db, site_product_id)
    if site_product.status == SiteProductStatus.PUBLISHED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="商品仍处于已发布状态,请先下架(Phase 4 发布流程)再解除绑定",
        )

    await db.delete(site_product)
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.UNBIND, entity_type="site_product",
        entity_id=str(site_product_id),
    )
    await db.commit()


@router.get("/publication-previews/{site_product_id}", response_model=PublicationPreviewResponse)
async def get_publication_preview(
    site_product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Merges the internal Product with this SiteProduct's override, exactly
    as Phase 4's publish step would send it to the remote platform — so
    operators can see precisely what will go out before anything is
    published. Purely a read: nothing is written or sent anywhere."""
    sp = await _get_site_product_or_404(db, site_product_id)
    product = (
        await db.execute(
            select(Product).where(Product.id == sp.product_id).options(selectinload(Product.assets))
        )
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="内部商品不存在")

    override = sp.override
    overridden_fields: list[str] = []

    def pick(field: str, override_value, base_value):
        if override_value is not None and override_value != [] :
            overridden_fields.append(field)
            return override_value
        return base_value

    title = pick("title", override.title, product.title)
    description = pick("description", override.description, product.description)
    price = pick("price", override.price, product.price)
    category = pick("category", override.category, product.category)
    tags = pick("tags", override.tags or None, [])
    asset_ids = (
        [uuid.UUID(a) for a in override.asset_ids]
        if override.asset_ids
        else [a.id for a in product.assets]
    )
    if override.asset_ids:
        overridden_fields.append("asset_ids")

    return PublicationPreviewResponse(
        site_product_id=sp.id,
        product_id=product.id,
        site_id=sp.site_id,
        title=title,
        description=description,
        price=price,
        category=category,
        tags=tags,
        asset_ids=asset_ids,
        overridden_fields=overridden_fields,
    )
