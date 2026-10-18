import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import AuditAction, ProductStatus, UserRole
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.schemas.product import (
    BulkUpdateRequest,
    BulkUpdateResponse,
    PagedResponse,
    ProductCreate,
    ProductDetailResponse,
    ProductResponse,
    ProductUpdate,
    VariantCreate,
    VariantResponse,
    VariantUpdate,
)
from app.services.audit import write_audit_log

router = APIRouter(prefix="/products", tags=["products"])

SORTABLE_FIELDS = {
    "created_at": Product.created_at,
    "updated_at": Product.updated_at,
    "title": Product.title,
    "price": Product.price,
    "sku": Product.sku,
}


@router.get("", response_model=PagedResponse)
async def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None, max_length=255),
    status_filter: ProductStatus | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None, max_length=255),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    if sort_by not in SORTABLE_FIELDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"不支持的排序字段: {sort_by}")

    stmt = select(Product)
    count_stmt = select(func.count()).select_from(Product)

    if search:
        like = f"%{search}%"
        condition = (Product.title.ilike(like)) | (Product.sku.ilike(like))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if status_filter:
        stmt = stmt.where(Product.status == status_filter)
        count_stmt = count_stmt.where(Product.status == status_filter)
    if category:
        stmt = stmt.where(Product.category == category)
        count_stmt = count_stmt.where(Product.category == category)

    column = SORTABLE_FIELDS[sort_by]
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    total = (await db.execute(count_stmt)).scalar_one()
    items = (await db.execute(stmt)).scalars().all()

    return PagedResponse(items=list(items), total=total, page=page, page_size=page_size)


@router.post("", response_model=ProductDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    existing = (
        await db.execute(select(Product.id).where(Product.sku == payload.sku))
    ).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="该 SKU 已存在")

    for v in payload.variants:
        dup = (await db.execute(select(ProductVariant.id).where(ProductVariant.sku == v.sku))).first()
        if dup:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=f"规格 SKU 已存在: {v.sku}")

    product = Product(
        sku=payload.sku,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        brand=payload.brand,
        status=payload.status,
        price=payload.price,
        cost_price=payload.cost_price,
        currency=payload.currency,
        attributes=payload.attributes,
        variants=[ProductVariant(**v.model_dump()) for v in payload.variants],
    )
    db.add(product)
    await db.flush()
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.CREATE, entity_type="product", entity_id=str(product.id)
    )
    await db.commit()
    await db.refresh(product)
    await db.refresh(product, attribute_names=["variants", "assets"])
    return product


async def _get_product_or_404(db: AsyncSession, product_id: uuid.UUID) -> Product:
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.variants), selectinload(Product.assets))
    )
    product = (await db.execute(stmt)).scalar_one_or_none()
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="商品不存在")
    return product


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await _get_product_or_404(db, product_id)


@router.patch("/{product_id}", response_model=ProductDetailResponse)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    product = await _get_product_or_404(db, product_id)
    if product.version != payload.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="数据已被其他人修改,请刷新后重试",
        )

    updates = payload.model_dump(exclude={"version"}, exclude_unset=True)
    for field, value in updates.items():
        setattr(product, field, value)

    await write_audit_log(
        db,
        user_id=user.id,
        action=AuditAction.UPDATE,
        entity_type="product",
        entity_id=str(product.id),
        details={"fields": list(updates.keys())},
    )
    await db.commit()
    await db.refresh(product)
    await db.refresh(product, attribute_names=["variants", "assets"])
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Archives rather than hard-deletes, per the project's data-safety
    default: destructive actions prefer archive/unpublish over permanent
    deletion. There is intentionally no hard-delete endpoint yet."""
    product = await _get_product_or_404(db, product_id)
    product.status = ProductStatus.ARCHIVED
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.ARCHIVE, entity_type="product", entity_id=str(product.id)
    )
    await db.commit()


@router.post("/bulk-update", response_model=BulkUpdateResponse)
async def bulk_update_products(
    payload: BulkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Bulk edit intentionally does not take per-row version numbers — the
    caller is choosing a small set of fields to apply uniformly across many
    rows, not resolving a specific conflict. Each affected row still gets
    its own version bumped so a concurrent single-row editor is protected."""
    found = (
        await db.execute(select(Product).where(Product.id.in_(payload.ids)))
    ).scalars().all()
    found_ids = {p.id for p in found}
    not_found_ids = [i for i in payload.ids if i not in found_ids]

    patch = payload.model_dump(exclude={"ids"}, exclude_unset=True, exclude_none=True)
    for product in found:
        for field, value in patch.items():
            setattr(product, field, value)

    await write_audit_log(
        db,
        user_id=user.id,
        action=AuditAction.BULK_UPDATE,
        entity_type="product",
        details={"ids": [str(i) for i in found_ids], "patch": patch},
    )
    await db.commit()
    return BulkUpdateResponse(updated_count=len(found_ids), not_found_ids=not_found_ids)


@router.post(
    "/{product_id}/variants", response_model=VariantResponse, status_code=status.HTTP_201_CREATED
)
async def add_variant(
    product_id: uuid.UUID,
    payload: VariantCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    await _get_product_or_404(db, product_id)
    dup = (await db.execute(select(ProductVariant.id).where(ProductVariant.sku == payload.sku))).first()
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="规格 SKU 已存在")

    variant = ProductVariant(product_id=product_id, **payload.model_dump())
    db.add(variant)
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.CREATE, entity_type="product_variant",
        entity_id=str(variant.id) if variant.id else "",
    )
    await db.commit()
    await db.refresh(variant)
    return variant


@router.patch("/{product_id}/variants/{variant_id}", response_model=VariantResponse)
async def update_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    payload: VariantUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    variant = (
        await db.execute(
            select(ProductVariant).where(
                ProductVariant.id == variant_id, ProductVariant.product_id == product_id
            )
        )
    ).scalar_one_or_none()
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="规格不存在")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, field, value)

    await write_audit_log(
        db, user_id=user.id, action=AuditAction.UPDATE, entity_type="product_variant",
        entity_id=str(variant.id),
    )
    await db.commit()
    await db.refresh(variant)
    return variant


@router.delete("/{product_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    variant = (
        await db.execute(
            select(ProductVariant).where(
                ProductVariant.id == variant_id, ProductVariant.product_id == product_id
            )
        )
    ).scalar_one_or_none()
    if variant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="规格不存在")

    await db.delete(variant)
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.DELETE, entity_type="product_variant",
        entity_id=str(variant_id),
    )
    await db.commit()
