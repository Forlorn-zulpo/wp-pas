"""Import every mapped model here so SQLAlchemy's relationship() string
references (e.g. relationship("Asset")) always resolve regardless of which
module happened to trigger the import first — and so Alembic autogenerate
and `Base.metadata.create_all()` always see the full schema."""

from app.models.user import User  # noqa: F401
from app.models.product import Product, ProductVariant  # noqa: F401
from app.models.asset import Asset  # noqa: F401
from app.models.audit import AuditLog, ImportJob  # noqa: F401
from app.models.site import Site  # noqa: F401
from app.models.site_product import (  # noqa: F401
    ExternalProductMapping,
    SiteProduct,
    SiteProductOverride,
)
from app.models.publication import PublicationJob, PublicationItem  # noqa: F401
