"""add pg_trgm GIN indexes for product title and sku search

Revision ID: e88c9266da52
Revises: 4b22fcd9eff3
Create Date: 2026-10-22 09:32:35.519275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e88c9266da52'
down_revision: Union[str, Sequence[str], None] = '4b22fcd9eff3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Without this, search_term ILIKE '%x%' can never use a plain B-tree
    index (the leading wildcard defeats it) and falls back to a sequential
    scan — fine at a few hundred rows, a real problem at the 5,000-50,000
    row scale this project targets. pg_trgm's GIN index supports ILIKE
    '%...%' directly."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_title_trgm_gin "
        "ON products USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_sku_trgm_gin "
        "ON products USING gin (sku gin_trgm_ops)"
    )
    # The old plain B-tree index on title (from the first migration) is
    # redundant for search now — equality/prefix lookups on title are rare,
    # ordering by title (sort_by=title) still uses it, so it stays.


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_products_sku_trgm_gin")
    op.execute("DROP INDEX IF EXISTS ix_products_title_trgm_gin")
