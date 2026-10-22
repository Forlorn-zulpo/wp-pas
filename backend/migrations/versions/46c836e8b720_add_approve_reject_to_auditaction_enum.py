"""add approve reject to auditaction enum

Revision ID: 46c836e8b720
Revises: 5ad4b286d0be
Create Date: 2026-10-22 00:15:56.467150

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46c836e8b720'
down_revision: Union[str, Sequence[str], None] = '5ad4b286d0be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'APPROVE'")
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'REJECT'")


def downgrade() -> None:
    raise NotImplementedError("Dropping enum values requires rebuilding the auditaction type.")
