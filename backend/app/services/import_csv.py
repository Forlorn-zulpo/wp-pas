import csv
import io
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ImportStatus, ProductStatus
from app.models.product import Product

REQUIRED_COLUMNS = {"sku", "title", "price"}
MAX_ERRORS_RECORDED = 200


class CsvImportError(Exception):
    pass


def _parse_row(row: dict, row_number: int) -> tuple[dict | None, dict | None]:
    sku = (row.get("sku") or "").strip()
    title = (row.get("title") or "").strip()
    price_raw = (row.get("price") or "").strip()

    if not sku:
        return None, {"row": row_number, "field": "sku", "message": "SKU 不能为空"}
    if not title:
        return None, {"row": row_number, "field": "title", "message": "标题不能为空"}
    try:
        price = Decimal(price_raw) if price_raw else Decimal("0")
    except InvalidOperation:
        return None, {"row": row_number, "field": "price", "message": f"价格格式不正确: {price_raw!r}"}
    if price < 0:
        return None, {"row": row_number, "field": "price", "message": "价格不能为负数"}

    return {
        "sku": sku,
        "title": title,
        "price": price,
        "category": (row.get("category") or "").strip(),
        "brand": (row.get("brand") or "").strip(),
        "description": (row.get("description") or "").strip(),
        "status": ProductStatus.DRAFT,
        "currency": (row.get("currency") or "USD").strip().upper()[:3] or "USD",
    }, None


async def process_csv_import(db: AsyncSession, content: bytes) -> dict:
    """Parses the CSV, validates each row with deterministic rules (per the
    project's collection-strategy principle: rules first, AI only for the
    genuinely ambiguous cases — a CSV import is fully structured, so no AI
    is involved here), and inserts valid rows. Returns a summary dict used
    to populate the ImportJob record. Duplicate SKUs (within the file or
    against existing products) are reported as row errors, not silently
    skipped or silently overwritten."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvImportError("文件编码不是 UTF-8,请另存为 UTF-8 编码的 CSV") from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        raise CsvImportError(f"CSV 缺少必需列: {', '.join(sorted(missing))}")

    valid_rows: list[dict] = []
    errors: list[dict] = []
    seen_skus: set[str] = set()
    total = 0

    for i, row in enumerate(reader, start=2):  # header is row 1
        total += 1
        parsed, error = _parse_row(row, i)
        if error:
            if len(errors) < MAX_ERRORS_RECORDED:
                errors.append(error)
            continue
        if parsed["sku"] in seen_skus:
            if len(errors) < MAX_ERRORS_RECORDED:
                errors.append({"row": i, "field": "sku", "message": f"文件内重复的 SKU: {parsed['sku']}"})
            continue
        seen_skus.add(parsed["sku"])
        valid_rows.append((i, parsed))

    existing_skus: set[str] = set()
    if seen_skus:
        existing = (
            await db.execute(select(Product.sku).where(Product.sku.in_(seen_skus)))
        ).scalars().all()
        existing_skus = set(existing)

    success_count = 0
    for row_number, parsed in valid_rows:
        if parsed["sku"] in existing_skus:
            if len(errors) < MAX_ERRORS_RECORDED:
                errors.append(
                    {"row": row_number, "field": "sku", "message": f"商品已存在,已跳过: {parsed['sku']}"}
                )
            continue
        db.add(Product(**parsed))
        success_count += 1

    error_count = total - success_count
    status = ImportStatus.COMPLETED if error_count == 0 else ImportStatus.COMPLETED_WITH_ERRORS
    if success_count == 0 and total > 0:
        status = ImportStatus.FAILED

    return {
        "total_rows": total,
        "success_rows": success_count,
        "error_rows": error_count,
        "errors": errors,
        "status": status,
    }
