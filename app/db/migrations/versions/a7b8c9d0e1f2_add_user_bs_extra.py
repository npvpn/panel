"""add user bs_extra remaining pool

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-06-30 10:42:12.051205

"""

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("bs_extra", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "bs_extra")
