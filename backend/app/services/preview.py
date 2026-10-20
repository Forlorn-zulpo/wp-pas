import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from app.models.product import Product
from app.models.site_product import SiteProductOverride


@dataclass
class MergedPreview:
    title: str
    description: str
    price: Decimal
    category: str
    tags: list
    asset_ids: list[uuid.UUID]
    overridden_fields: list[str] = field(default_factory=list)


def merge_product_with_override(product: Product, override: SiteProductOverride) -> MergedPreview:
    """The single place that combines an internal Product with a site's
    override. Both the read-only publication-preview endpoint and the
    actual publish flow call this, so what an operator previews is always
    exactly what gets sent — there is no second code path that could drift."""
    overridden_fields: list[str] = []

    def pick(field_name: str, override_value, base_value):
        if override_value is not None and override_value != []:
            overridden_fields.append(field_name)
            return override_value
        return base_value

    title = pick("title", override.title, product.title)
    description = pick("description", override.description, product.description)
    price = pick("price", override.price, product.price)
    category = pick("category", override.category, product.category)
    tags = pick("tags", override.tags or None, [])

    if override.asset_ids:
        asset_ids = [uuid.UUID(a) for a in override.asset_ids]
        overridden_fields.append("asset_ids")
    else:
        asset_ids = [a.id for a in product.assets]

    return MergedPreview(
        title=title,
        description=description,
        price=price,
        category=category,
        tags=tags,
        asset_ids=asset_ids,
        overridden_fields=overridden_fields,
    )
