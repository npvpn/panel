"""node roles cascade

Revision ID: a98d3011a530
Revises: 5a20cee1a4e9
Create Date: 2026-06-12 00:25:07.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a98d3011a530'
down_revision = '5a20cee1a4e9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_mysql = bind.engine.name == "mysql"
    tag_collation = "utf8mb4_bin" if is_mysql else None

    op.add_column(
        "nodes",
        sa.Column(
            "role",
            sa.Enum("entry", "exit", "direct", name="noderole"),
            nullable=False,
            server_default="direct",
        ),
    )
    op.add_column("nodes", sa.Column("cascade_params", sa.JSON(), nullable=True))

    op.create_table(
        "cascade_routes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_node_id", sa.Integer(), nullable=False),
        sa.Column("exit_node_id", sa.Integer(), nullable=False),
        sa.Column("entry_inbound_tag", sa.String(length=256, collation=tag_collation), nullable=False),
        sa.ForeignKeyConstraint(["entry_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exit_node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entry_inbound_tag"], ["inbounds.tag"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("cascade_routes")
    op.drop_column("nodes", "cascade_params")
    op.drop_column("nodes", "role")
