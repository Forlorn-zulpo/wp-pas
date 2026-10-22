import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import AuditAction, ReviewStatus, SiteProductStatus, UserRole
from app.models.review import ReviewItem
from app.models.site_product import SiteProduct
from app.models.user import User
from app.schemas.review import ReviewDecision, ReviewItemResponse, ReviewRequest
from app.services.audit import write_audit_log

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewItemResponse, status_code=status.HTTP_201_CREATED)
async def request_review(
    payload: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    sp = (
        await db.execute(select(SiteProduct).where(SiteProduct.id == payload.site_product_id))
    ).scalar_one_or_none()
    if sp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="站点商品绑定不存在")

    existing_pending = (
        await db.execute(
            select(ReviewItem.id).where(
                ReviewItem.site_product_id == payload.site_product_id,
                ReviewItem.status == ReviewStatus.PENDING,
            )
        )
    ).first()
    if existing_pending:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="该绑定已有待处理的审核请求")

    review = ReviewItem(site_product_id=payload.site_product_id, requested_by=user.id, notes=payload.notes)
    sp.status = SiteProductStatus.PENDING_REVIEW
    db.add(review)
    await write_audit_log(db, user_id=user.id, action=AuditAction.CREATE, entity_type="review_item")
    await db.commit()
    await db.refresh(review)
    return review


@router.get("", response_model=list[ReviewItemResponse])
async def list_reviews(
    review_status: ReviewStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.REVIEWER)),
):
    stmt = select(ReviewItem)
    if review_status:
        stmt = stmt.where(ReviewItem.status == review_status)
    rows = (await db.execute(stmt.order_by(ReviewItem.created_at.desc()))).scalars().all()
    return list(rows)


async def _get_review_or_404(db: AsyncSession, review_id: uuid.UUID) -> ReviewItem:
    review = (await db.execute(select(ReviewItem).where(ReviewItem.id == review_id))).scalar_one_or_none()
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="审核记录不存在")
    return review


@router.post("/{review_id}/approve", response_model=ReviewItemResponse)
async def approve_review(
    review_id: uuid.UUID,
    payload: ReviewDecision,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
):
    review = await _get_review_or_404(db, review_id)
    if review.status != ReviewStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="该审核已处理,不能重复操作")

    sp = (
        await db.execute(select(SiteProduct).where(SiteProduct.id == review.site_product_id))
    ).scalar_one_or_none()

    review.status = ReviewStatus.APPROVED
    review.reviewed_by = user.id
    review.reviewed_at = datetime.now(timezone.utc)
    review.notes = payload.notes or review.notes
    if sp:
        sp.status = SiteProductStatus.APPROVED

    await write_audit_log(db, user_id=user.id, action=AuditAction.APPROVE, entity_type="review_item",
                           entity_id=str(review.id))
    await db.commit()
    await db.refresh(review)
    return review


@router.post("/{review_id}/reject", response_model=ReviewItemResponse)
async def reject_review(
    review_id: uuid.UUID,
    payload: ReviewDecision,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER)),
):
    review = await _get_review_or_404(db, review_id)
    if review.status != ReviewStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="该审核已处理,不能重复操作")

    sp = (
        await db.execute(select(SiteProduct).where(SiteProduct.id == review.site_product_id))
    ).scalar_one_or_none()

    review.status = ReviewStatus.REJECTED
    review.reviewed_by = user.id
    review.reviewed_at = datetime.now(timezone.utc)
    review.notes = payload.notes or review.notes
    if sp:
        sp.status = SiteProductStatus.BOUND  # back to bound, not published

    await write_audit_log(db, user_id=user.id, action=AuditAction.REJECT, entity_type="review_item",
                           entity_id=str(review.id))
    await db.commit()
    await db.refresh(review)
    return review
