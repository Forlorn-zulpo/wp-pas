"""add deepseek to aiprovidertype enum

Revision ID: 4b22fcd9eff3
Revises: 46c836e8b720
Create Date: 2026-10-22 09:15:13.207858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b22fcd9eff3'
down_revision: Union[str, Sequence[str], None] = '46c836e8b720'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE aiprovidertype ADD VALUE IF NOT EXISTS 'DEEPSEEK'")


def downgrade() -> None:
    raise NotImplementedError("Dropping enum values requires rebuilding the aiprovidertype type.")
