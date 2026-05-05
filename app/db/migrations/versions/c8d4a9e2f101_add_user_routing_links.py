"""add user routing links

Revision ID: c8d4a9e2f101
Revises: 9f4a1b2c3d4e
Create Date: 2026-05-04 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c8d4a9e2f101"
down_revision = "9f4a1b2c3d4e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("sub_routing_happ", sa.String(length=4096), nullable=True))
        batch_op.add_column(sa.Column("sub_routing_v2raytun", sa.String(length=4096), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("sub_routing_v2raytun")
        batch_op.drop_column("sub_routing_happ")
