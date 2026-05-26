"""add host bot association

Revision ID: e2a71b4c8d9f
Revises: f0b1c2d3e4f5
Create Date: 2026-05-25 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e2a71b4c8d9f"
down_revision = "f0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "host_bot_association",
        sa.Column("host_id", sa.Integer(), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["host_id"], ["hosts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("host_id", "bot_id"),
    )


def downgrade() -> None:
    op.drop_table("host_bot_association")
