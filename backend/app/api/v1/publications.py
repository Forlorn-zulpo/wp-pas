import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.enums import (
    AuditAction,
    PublicationItemStatus,
    PublicationJobStatus,
    SiteProductStatus,
    UserRole,
)
from app.models.publication import PublicationItem, PublicationJob
from app.models.site import Site
from app.models.site_product import SiteProduct
from app.models.user import User
from app.schemas.publication import PublicationJobCreate, PublicationJobResponse
from app.services.audit import write_audit_log
from app.services.publishing import publish_one

router = APIRouter(prefix="/publications", tags=["publications"])


async def _run_items(db: AsyncSession, items: list[PublicationItem], site: Site) -> tuple[int, int]:
    """Publishes exactly the given items and returns (success_count,
    failed_count). A pure helper over a list of items — not a PublicationJob
    object — so retry-failed can reuse it against a subset of an existing
    job's items without constructing a second ORM object sharing that job's
    primary key (which would conflict with SQLAlchemy's identity map)."""
    success_count = 0
    failed_count = 0

    for item in items:
        sp = (
            await db.execute(
                select(SiteProduct)
                .where(SiteProduct.id == item.site_product_id)
                .options(selectinload(SiteProduct.override), selectinload(SiteProduct.external_mapping))
            )
        ).scalar_one_or_none()
        if sp is None:
            item.status = PublicationItemStatus.FAILED
            item.error_message = "站点商品绑定不存在"
            item.attempt_count += 1
            failed_count += 1
            continue

        item.attempt_count += 1

        if sp.status == SiteProductStatus.PENDING_REVIEW:
            item.status = PublicationItemStatus.FAILED
            item.error_message = "该商品处于待审核状态,审核通过前不能发布"
            failed_count += 1
            await db.flush()
            continue

        item.status = PublicationItemStatus.PROCESSING
        result = await publish_one(db, sp, site)

        if result.success:
            item.status = PublicationItemStatus.SUCCESS
            item.external_id = result.external_id
            item.error_message = ""
            success_count += 1
            sp.status = SiteProductStatus.PUBLISHED
            if sp.external_mapping:
                sp.external_mapping.external_id = result.external_id
        else:
            item.status = PublicationItemStatus.FAILED
            item.error_message = result.error
            failed_count += 1
            sp.status = SiteProductStatus.FAILED

        await db.flush()

    return success_count, failed_count


def _job_status_from_counts(success: int, failed: int) -> PublicationJobStatus:
    if failed == 0:
        return PublicationJobStatus.COMPLETED
    if success == 0:
        return PublicationJobStatus.FAILED
    return PublicationJobStatus.PARTIAL


@router.post("", response_model=PublicationJobResponse, status_code=status.HTTP_201_CREATED)
async def create_and_run_publication_job(
    payload: PublicationJobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    site = (await db.execute(select(Site).where(Site.id == payload.site_id))).scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="站点不存在")

    bound = (
        await db.execute(
            select(SiteProduct.id).where(
                SiteProduct.id.in_(payload.site_product_ids), SiteProduct.site_id == payload.site_id
            )
        )
    ).scalars().all()
    missing = set(payload.site_product_ids) - set(bound)
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"以下绑定不存在或不属于该站点: {', '.join(str(m) for m in missing)}",
        )

    job = PublicationJob(
        site_id=payload.site_id,
        created_by=user.id,
        status=PublicationJobStatus.PROCESSING,
        total_items=len(payload.site_product_ids),
        items=[PublicationItem(site_product_id=spid) for spid in payload.site_product_ids],
    )
    db.add(job)
    await db.flush()

    success_count, failed_count = await _run_items(db, job.items, site)
    job.success_items = success_count
    job.failed_items = failed_count
    job.status = _job_status_from_counts(success_count, failed_count)

    await write_audit_log(
        db, user_id=user.id, action=AuditAction.PUBLISH, entity_type="publication_job",
        entity_id=str(job.id),
        details={"site_id": str(site.id), "success": job.success_items, "failed": job.failed_items},
    )
    await db.commit()
    await db.refresh(job, attribute_names=["items"])
    return job


@router.get("", response_model=list[PublicationJobResponse])
async def list_publication_jobs(
    site_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.REVIEWER)),
):
    stmt = select(PublicationJob).options(selectinload(PublicationJob.items))
    if site_id:
        stmt = stmt.where(PublicationJob.site_id == site_id)
    jobs = (await db.execute(stmt.order_by(PublicationJob.created_at.desc()).limit(50))).scalars().all()
    return list(jobs)


async def _get_job_or_404(db: AsyncSession, job_id: uuid.UUID) -> PublicationJob:
    job = (
        await db.execute(
            select(PublicationJob)
            .where(PublicationJob.id == job_id)
            .options(selectinload(PublicationJob.items))
        )
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="发布任务不存在")
    return job


@router.get("/{job_id}", response_model=PublicationJobResponse)
async def get_publication_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.REVIEWER)),
):
    return await _get_job_or_404(db, job_id)


@router.post("/{job_id}/retry-failed", response_model=PublicationJobResponse)
async def retry_failed_items(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Retries only the items that failed — successful items in the same
    job are left untouched, per the project's "failed tasks are retried
    independently" requirement."""
    job = await _get_job_or_404(db, job_id)
    site = (await db.execute(select(Site).where(Site.id == job.site_id))).scalar_one_or_none()
    if site is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="站点不存在")

    failed_items = [i for i in job.items if i.status == PublicationItemStatus.FAILED]
    if not failed_items:
        return job

    job.status = PublicationJobStatus.PROCESSING
    retried_success, retried_failed = await _run_items(db, failed_items, site)
    job.success_items += retried_success
    job.failed_items = retried_failed
    job.status = _job_status_from_counts(job.success_items, job.failed_items)

    await write_audit_log(
        db, user_id=user.id, action=AuditAction.PUBLISH, entity_type="publication_job",
        entity_id=str(job.id), details={"retry": True, "retried_items": len(failed_items)},
    )
    await db.commit()
    await db.refresh(job, attribute_names=["items"])
    return job
