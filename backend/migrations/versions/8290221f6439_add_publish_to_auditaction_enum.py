"""add publish to auditaction enum

Revision ID: 8290221f6439
Revises: edd544947b89
Create Date: 2026-10-18 23:00:21.502726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8290221f6439'
down_revision: Union[str, Sequence[str], None] = 'edd544947b89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'PUBLISH'")


def downgrade() -> None:
    raise NotImplementedError(
        "Dropping enum values requires rebuilding the auditaction type; not supported by this migration."
    )
