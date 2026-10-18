import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.asset import Asset
from app.models.enums import AssetStatus, AuditAction, UserRole
from app.models.product import Product
from app.schemas.product import AssetResponse
from app.services.audit import write_audit_log
from app.services.storage import get_storage_service

router = APIRouter(tags=["assets"])


@router.post(
    "/products/{product_id}/assets",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset(
    product_id: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    product = (
        await db.execute(select(Product.id).where(Product.id == product_id))
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="商品不存在")

    if file.content_type not in settings.ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"不支持的文件类型: {file.content_type}。仅支持 {', '.join(settings.ALLOWED_IMAGE_CONTENT_TYPES)}",
        )

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件超过大小上限 ({settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB)",
        )

    # Validate it's actually a decodable image, not just a file with a
    # spoofed content-type header (defends against disguised-file uploads).
    width = height = None
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
        with Image.open(io.BytesIO(content)) as img:
            width, height = img.size
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="文件不是有效的图片"
        ) from exc

    extension = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(file.content_type, "")

    storage = get_storage_service()
    storage_key = storage.save(content, extension=extension)

    # First image for a product becomes primary automatically.
    existing_ids = (
        await db.execute(select(Asset.id).where(Asset.product_id == product_id))
    ).scalars().all()

    asset = Asset(
        product_id=product_id,
        storage_key=storage_key,
        original_filename=file.filename or "",
        content_type=file.content_type,
        size_bytes=len(content),
        width=width,
        height=height,
        position=len(existing_ids),
        is_primary=len(existing_ids) == 0,
        status=AssetStatus.READY,
    )
    db.add(asset)
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.CREATE, entity_type="asset",
        details={"product_id": str(product_id), "filename": file.filename},
    )
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("/assets/{asset_id}/file")
async def get_asset_file(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    asset = (await db.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="图片不存在")

    storage = get_storage_service()
    file_path = storage.path_for(asset.storage_key)
    return FileResponse(file_path, media_type=asset.content_type)


@router.post("/assets/{asset_id}/primary", response_model=AssetResponse)
async def set_primary_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    asset = (await db.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="图片不存在")

    await db.execute(
        update(Asset).where(Asset.product_id == asset.product_id).values(is_primary=False)
    )
    asset.is_primary = True
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.UPDATE, entity_type="asset", entity_id=str(asset.id),
        details={"set_primary": True},
    )
    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    """Hard-deletes the asset row and the underlying file. Unlike products,
    an uploaded image with no further use has no audit/compliance reason to
    be preserved, so this does not follow the archive-first default."""
    asset = (await db.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="图片不存在")

    storage = get_storage_service()
    storage.delete(asset.storage_key)

    await db.delete(asset)
    await write_audit_log(
        db, user_id=user.id, action=AuditAction.DELETE, entity_type="asset", entity_id=str(asset_id)
    )
    await db.commit()
