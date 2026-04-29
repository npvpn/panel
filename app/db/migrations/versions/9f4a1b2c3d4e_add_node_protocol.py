"""add node protocol

Revision ID: 9f4a1b2c3d4e
Revises: 6d2f9e1a4b7c
Create Date: 2026-04-29 10:58:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "9f4a1b2c3d4e"
down_revision = "6d2f9e1a4b7c"
branch_labels = None
depends_on = None


nodeprotocol_enum = sa.Enum("rest", "rpyc", name="nodeprotocol")


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        nodeprotocol_enum.create(bind, checkfirst=True)

    with op.batch_alter_table("nodes") as batch_op:
        batch_op.add_column(
            sa.Column(
                "protocol",
                nodeprotocol_enum,
                nullable=False,
                server_default="rest",
            )
        )

    op.execute("UPDATE nodes SET protocol = 'rest' WHERE protocol IS NULL")


def downgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("nodes") as batch_op:
        batch_op.drop_column("protocol")

    if bind.dialect.name == "postgresql":
        nodeprotocol_enum.drop(bind, checkfirst=True)
