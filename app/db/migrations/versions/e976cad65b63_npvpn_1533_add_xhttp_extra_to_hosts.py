"""npvpn_1533_add_xhttp_extra_to_hosts

Revision ID: e976cad65b63
Revises: a7b8c9d0e1f2
Create Date: 2026-07-08 15:07:58.493451

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e976cad65b63'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hosts", sa.Column("xhttp_extra", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("hosts", "xhttp_extra")
