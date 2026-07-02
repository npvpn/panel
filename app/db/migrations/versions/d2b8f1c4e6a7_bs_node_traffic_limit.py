"""bs node traffic limit

Revision ID: d2b8f1c4e6a7
Revises: c1a7e4b9d2f3
Create Date: 2026-06-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd2b8f1c4e6a7'
down_revision = 'c1a7e4b9d2f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("nodes", sa.Column("is_bs", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    op.create_table(
        "node_user_bs_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("monthly_used", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("monthly_period", sa.String(length=7), nullable=True),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("node_id", "user_id", name="uq_node_user_bs_usage"),
    )
    op.create_index("ix_node_user_bs_usage_node_id", "node_user_bs_usage", ["node_id"])
    op.create_index("ix_node_user_bs_usage_user_id", "node_user_bs_usage", ["user_id"])

    op.create_table(
        "node_user_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("period", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("node_id", "user_id", name="uq_node_user_blocks"),
    )
    op.create_index("ix_node_user_blocks_node_id", "node_user_blocks", ["node_id"])
    op.create_index("ix_node_user_blocks_user_id", "node_user_blocks", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_node_user_blocks_user_id", table_name="node_user_blocks")
    op.drop_index("ix_node_user_blocks_node_id", table_name="node_user_blocks")
    op.drop_table("node_user_blocks")
    op.drop_index("ix_node_user_bs_usage_user_id", table_name="node_user_bs_usage")
    op.drop_index("ix_node_user_bs_usage_node_id", table_name="node_user_bs_usage")
    op.drop_table("node_user_bs_usage")
    op.drop_column("nodes", "is_bs")
