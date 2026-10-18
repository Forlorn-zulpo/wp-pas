import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.audit import ImportJob
from app.models.enums import AuditAction, ImportStatus, UserRole
from app.schemas.product import ImportJobResponse
from app.services.audit import write_audit_log
from app.services.import_csv import CsvImportError, process_csv_import

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("", response_model=ImportJobResponse, status_code=status.HTTP_201_CREATED)
async def import_products_csv(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Synchronous for now: a 5,000–50,000 row catalog's CSV import is
    seconds of work, well within a request timeout. Phase 7 should move this
    onto Celery (matching the "long tasks return a job id immediately"
    principle) once import volume or processing complexity (e.g. per-row AI
    enrichment) makes synchronous processing too slow — the ImportJob row
    already models that async shape, so only the trigger needs to change."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="仅支持 .csv 文件")

    content = await file.read()
    job = ImportJob(filename=file.filename or "import.csv", created_by=user.id, status=ImportStatus.PROCESSING)
    db.add(job)
    await db.flush()

    try:
        result = await process_csv_import(db, content)
    except CsvImportError as exc:
        job.status = ImportStatus.FAILED
        job.errors = [{"row": 0, "field": "file", "message": str(exc)}]
        await db.commit()
        await db.refresh(job)
        return job

    job.status = result["status"]
    job.total_rows = result["total_rows"]
    job.success_rows = result["success_rows"]
    job.error_rows = result["error_rows"]
    job.errors = result["errors"]

    await write_audit_log(
        db, user_id=user.id, action=AuditAction.IMPORT, entity_type="import_job", entity_id=str(job.id),
        details={"success_rows": job.success_rows, "error_rows": job.error_rows},
    )
    await db.commit()
    await db.refresh(job)
    return job


@router.get("", response_model=list[ImportJobResponse])
async def list_imports(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.REVIEWER)),
):
    jobs = (
        await db.execute(select(ImportJob).order_by(ImportJob.created_at.desc()).limit(50))
    ).scalars().all()
    return list(jobs)


@router.get("/{job_id}", response_model=ImportJobResponse)
async def get_import(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR, UserRole.REVIEWER)),
):
    job = (await db.execute(select(ImportJob).where(ImportJob.id == job_id))).scalar_one_or_none()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="导入记录不存在")
    return job
