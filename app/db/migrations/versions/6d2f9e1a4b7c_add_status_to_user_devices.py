"""add status to user_devices

Revision ID: 6d2f9e1a4b7c
Revises: a1c2e3f4b5d6
Create Date: 2026-04-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "6d2f9e1a4b7c"
down_revision = "a1c2e3f4b5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_devices") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=16), nullable=False, server_default="active")
        )


def downgrade() -> None:
    with op.batch_alter_table("user_devices") as batch_op:
        batch_op.drop_column("status")
