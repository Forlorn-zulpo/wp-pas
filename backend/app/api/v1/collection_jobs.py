import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.collection_job import CollectionJob
from app.models.enums import AuditAction, CollectionJobStatus, UserRole
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.collection_job import CollectionJobCreate, CollectionJobResponse
from app.services.audit import write_audit_log

router = APIRouter(prefix="/collection-jobs", tags=["collection-jobs"])


@router.post("", response_model=CollectionJobResponse, status_code=status.HTTP_201_CREATED)
async def create_collection_job(
    payload: CollectionJobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Creates the job record only — does not execute a scrape. Per-supplier
    collectors (the actual API/HTTP-parsing/browser-automation code, chosen
    per the project's collection-method principle) are implemented against
    a real supplier's real site/API in Phase 6, since writing one against no
    real target would mean either faking data or guessing at a site
    structure that doesn't exist. This job sits PENDING until that
    supplier's collector is wired in and calls its own executor."""
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
