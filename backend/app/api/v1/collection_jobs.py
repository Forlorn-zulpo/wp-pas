import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.collection_job import CollectionJob
from app.models.enums import AuditAction, CollectionJobStatus, ProductStatus, UserRole
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.collection_job import CollectionJobCreate, CollectionJobResponse
from app.services.audit import write_audit_log
from app.services.collectors.books_toscrape import BooksToScrapeCollector
from app.services.collectors.http_static import CollectorError

router = APIRouter(prefix="/collection-jobs", tags=["collection-jobs"])

# Registry of real per-supplier collectors. Only one entry exists for real
# here: "books_toscrape", the demo/sandbox target used to prove the
# HTTP_STATIC collection path end to end (see
# app/services/collectors/books_toscrape.py's docstring for why). A real
# supplier gets its own key here once a real target is provided — adding
# one is "write a collector subclass, register it here," nothing else in
# this file changes.
COLLECTOR_REGISTRY = {
    "books_toscrape": BooksToScrapeCollector,
}


@router.post("", response_model=CollectionJobResponse, status_code=status.HTTP_201_CREATED)
async def create_collection_job(
    payload: CollectionJobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Creates the job and, if target_config names a registered collector
    key, runs it synchronously (same documented trade-off as CSV import and
    publishing — see their docstrings; Phase 7 Celery migration applies
    here too). target_config = {"collector": "books_toscrape", "start_url":
    "https://..."}. If the collector key isn't registered, the job is
    created PENDING and left for a human to notice — it does NOT silently
    pretend to have collected anything."""
    supplier = (
        await db.execute(select(Supplier.id).where(Supplier.id == payload.supplier_id))
    ).scalar_one_or_none()
    if supplier is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="供应商不存在")

    job = CollectionJob(
        supplier_id=payload.supplier_id, created_by=user.id, target_config=payload.target_config,
        status=CollectionJobStatus.PENDING,
    )
    db.add(job)
    await db.flush()

    collector_key = payload.target_config.get("collector")
    start_url = payload.target_config.get("start_url")
    collector_cls = COLLECTOR_REGISTRY.get(collector_key)

    if collector_cls and start_url:
        job.status = CollectionJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        await db.flush()

        try:
            collector = collector_cls()
            products, errors = await collector.collect(start_url, max_pages=payload.target_config.get("max_pages", 5))
        except CollectorError as exc:
            job.status = CollectionJobStatus.FAILED
            job.errors = [{"message": str(exc)}]
            job.finished_at = datetime.now(timezone.utc)
            await write_audit_log(db, user_id=user.id, action=AuditAction.CREATE, entity_type="collection_job")
            await db.commit()
            await db.refresh(job)
            return job

        success_count = 0
        for item in products:
            existing = (
                await db.execute(select(Product.id).where(Product.sku == item.sku))
            ).scalar_one_or_none() if item.sku else None
            if existing:
                errors.append({"url": item.source_url, "message": f"商品已存在,已跳过: {item.sku}"})
                continue
            db.add(
                Product(
                    sku=item.sku or f"COLLECTED-{uuid.uuid4().hex[:12]}",
                    title=item.title,
                    description=item.description,
                    category=item.category,
                    price=item.price or "0",
                    currency=item.currency,
                    status=ProductStatus.DRAFT,  # collected products always start as drafts for review
                    supplier_id=payload.supplier_id,
                    attributes={"source_url": item.source_url, "in_stock": item.in_stock},
                )
            )
            success_count += 1

        job.total_items = len(products)
        job.success_items = success_count
        job.error_items = len(errors)
        job.errors = errors[:200]
        job.status = (
            CollectionJobStatus.COMPLETED if not errors
            else (CollectionJobStatus.COMPLETED_WITH_ERRORS if success_count > 0 else CollectionJobStatus.FAILED)
        )
        job.finished_at = datetime.now(timezone.utc)

    await write_audit_log(db, user_id=user.id, action=AuditAction.CREATE, entity_type="collection_job")
    await db.commit()
    await db.refresh(job)
    return job


@router.get("", response_model=list[CollectionJobResponse])
async def list_collection_jobs(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    rows = (
        await db.execute(select(CollectionJob).order_by(CollectionJob.created_at.desc()).limit(50))
    ).scalars().all()
    return list(rows)


@router.get("/{job_id}", response_model=CollectionJobResponse)
async def get_collection_job(
    job_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)
):
    job = (await db.execute(select(CollectionJob).where(CollectionJob.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="采集任务不存在")
    return job
