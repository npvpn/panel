"""node cascade balancer strategy

Revision ID: e1f2a3b4c5d6
Revises: d2b8f1c4e6a7
Create Date: 2026-06-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd2b8f1c4e6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "nodes",
        sa.Column(
            "cascade_balancer_strategy",
            sa.Enum("random", "roundRobin", "leastPing", "leastLoad",
                    name="nodebalancerstrategy"),
            nullable=False,
            server_default="random",
        ),
    )


def downgrade() -> None:
    op.drop_column("nodes", "cascade_balancer_strategy")
