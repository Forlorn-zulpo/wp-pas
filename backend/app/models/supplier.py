from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import CollectionMethod, SupplierStatus
from app.models.mixins import TimestampMixin, UUIDPKMixin, VersionedMixin


class Supplier(UUIDPKMixin, TimestampMixin, VersionedMixin, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    status: Mapped[SupplierStatus] = mapped_column(default=SupplierStatus.ACTIVE, nullable=False)

    # How to collect from this supplier — chosen per the project's collection
    # strategy: API first, then static HTTP/parsing, browser automation only
    # when genuinely required, manual when there's nothing to automate yet.
    collection_method: Mapped[CollectionMethod] = mapped_column(
        default=CollectionMethod.MANUAL, nullable=False
    )
    # Encrypted (Fernet, same scheme as Site credentials) when non-empty —
    # API keys or scraper auth for this supplier, if any.
    encrypted_credentials: Mapped[str | None] = mapped_column(Text, nullable=True)
    collection_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
