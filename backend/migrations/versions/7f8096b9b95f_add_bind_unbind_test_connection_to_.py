"""add bind unbind test_connection to auditaction enum

Revision ID: 7f8096b9b95f
Revises: 00b4e2901772
Create Date: 2026-10-18 22:55:54.924620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f8096b9b95f'
down_revision: Union[str, Sequence[str], None] = '00b4e2901772'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Postgres requires ADD VALUE to run outside the migration's normal
    transaction (a new enum value cannot be used in the same transaction
    that creates it on older Postgres, and some versions disallow it inside
    a transaction block entirely)."""
    with op.get_context().autocommit_block():
        # SQLAlchemy's Enum column stores the Python Enum member's NAME
        # (e.g. "BIND"), not its `.value` (e.g. "bind") — matching the
        # existing rows ('CREATE', 'UPDATE', ...) from the first migration.
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'BIND'")
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'UNBIND'")
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'TEST_CONNECTION'")


def downgrade() -> None:
    """Postgres cannot drop a single enum value. A real rollback would
    require rebuilding the enum type (rename, create new, migrate rows,
    drop old) — intentionally not implemented here since this project has
    no rows using the old 'auditaction' values that would need remapping
    for a downgrade to make sense outside of a full type rebuild."""
    raise NotImplementedError(
        "Dropping enum values requires rebuilding the auditaction type; not supported by this migration."
    )
