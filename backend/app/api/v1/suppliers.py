import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_credentials
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import AuditAction, UserRole
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate
from app.services.audit import write_audit_log

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _to_response(s: Supplier) -> SupplierResponse:
    return SupplierResponse(
        id=s.id, name=s.name, website=s.website, status=s.status,
        collection_method=s.collection_method, has_credentials=bool(s.encrypted_credentials),
        collection_config=s.collection_config, notes=s.notes, version=s.version, created_at=s.created_at,
    )


@router.get("", response_model=list[SupplierResponse])
async def list_suppliers(db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)):
    rows = (await db.execute(select(Supplier).order_by(Supplier.created_at.desc()))).scalars().all()
    return [_to_response(s) for s in rows]


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    supplier = Supplier(
        name=payload.name, website=payload.website, collection_method=payload.collection_method,
        encrypted_credentials=encrypt_credentials(payload.credentials) if payload.credentials else None,
        collection_config=payload.collection_config, notes=payload.notes,
    )
    db.add(supplier)
    await write_audit_log(db, user_id=user.id, action=AuditAction.CREATE, entity_type="supplier")
    await db.commit()
    await db.refresh(supplier)
    return _to_response(supplier)


async def _get_or_404(db: AsyncSession, supplier_id: uuid.UUID) -> Supplier:
    s = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalar_one_or_none()
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="供应商不存在")
    return s


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: uuid.UUID, db: AsyncSession = Depends(get_db), _user: User = Depends(get_current_user)
):
    return _to_response(await _get_or_404(db, supplier_id))


@router.patch("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    supplier = await _get_or_404(db, supplier_id)
    if supplier.version != payload.version:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="数据已被其他人修改,请刷新后重试")

    updates = payload.model_dump(exclude={"version", "credentials"}, exclude_unset=True)
    for field, value in updates.items():
        setattr(supplier, field, value)
    if "credentials" in payload.model_fields_set:
        supplier.encrypted_credentials = (
            encrypt_credentials(payload.credentials) if payload.credentials else None
        )

    await write_audit_log(db, user_id=user.id, action=AuditAction.UPDATE, entity_type="supplier",
                           entity_id=str(supplier.id))
    await db.commit()
    await db.refresh(supplier)
    return _to_response(supplier)
