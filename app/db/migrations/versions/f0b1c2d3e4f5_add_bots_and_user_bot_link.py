"""add bots and bot settings

Revision ID: f0b1c2d3e4f5
Revises: c8d4a9e2f101
Create Date: 2026-05-12 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f0b1c2d3e4f5"
down_revision = "c8d4a9e2f101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_bots_username"), "bots", ["username"], unique=True)

    op.create_table(
        "bot_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bot_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["bot_id"], ["bots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bot_id"),
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("bot_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_bot_id"), ["bot_id"], unique=False)
        batch_op.create_foreign_key("fk_users_bot_id_bots", "bots", ["bot_id"], ["id"])
        batch_op.drop_column("sub_routing_v2raytun")
        batch_op.drop_column("sub_routing_happ")
        batch_op.drop_column("sub_profile_title")
        batch_op.drop_column("sub_support_url")


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("sub_support_url", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("sub_profile_title", sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column("sub_routing_happ", sa.String(length=4096), nullable=True))
        batch_op.add_column(sa.Column("sub_routing_v2raytun", sa.String(length=4096), nullable=True))
        batch_op.drop_constraint("fk_users_bot_id_bots", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_users_bot_id"))
        batch_op.drop_column("bot_id")

    op.drop_table("bot_settings")
    op.drop_index(op.f("ix_bots_username"), table_name="bots")
    op.drop_table("bots")
