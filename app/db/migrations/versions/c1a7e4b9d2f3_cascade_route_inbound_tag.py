"""cascade route inbound tag

Revision ID: c1a7e4b9d2f3
Revises: a98d3011a530
Create Date: 2026-06-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1a7e4b9d2f3'
down_revision = 'a98d3011a530'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_mysql = bind.engine.name == "mysql"
    tag_collation = "utf8mb4_bin" if is_mysql else None

    op.add_column(
        "cascade_routes",
        sa.Column(
            "cascade_inbound_tag",
            sa.String(length=256, collation=tag_collation),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_cascade_routes_cascade_inbound_tag",
        "cascade_routes",
        "inbounds",
        ["cascade_inbound_tag"],
        ["tag"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_cascade_routes_cascade_inbound_tag", "cascade_routes", type_="foreignkey"
    )
    op.drop_column("cascade_routes", "cascade_inbound_tag")
