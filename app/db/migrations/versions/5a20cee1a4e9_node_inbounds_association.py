"""node inbounds association

Revision ID: 5a20cee1a4e9
Revises: e2a71b4c8d9f
Create Date: 2026-06-11 18:15:44.051344

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a20cee1a4e9'
down_revision = 'e2a71b4c8d9f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "node_inbounds",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("inbound_tag", sa.String(length=256), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inbound_tag"], ["inbounds.tag"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "inbound_tag"),
    )


def downgrade() -> None:
    op.drop_table("node_inbounds")
