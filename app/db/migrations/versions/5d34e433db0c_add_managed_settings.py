"""add managed_settings

Revision ID: 5d34e433db0c
Revises: c17a0aab3738
Create Date: 2026-07-16 18:25:31.919296

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d34e433db0c'
down_revision = 'c17a0aab3738'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "managed_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("scope", sa.String(length=16), nullable=False, server_default="global"),
        sa.Column("source", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("version", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("managed_settings")
