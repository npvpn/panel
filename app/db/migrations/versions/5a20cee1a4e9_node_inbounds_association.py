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
    # На MySQL inbounds.tag имеет collation utf8mb4_bin (см. миграцию
    # dd725e4d3628_fix_mysql_collations). FK требует совпадения типа/collation,
    # иначе ошибка 3780. На прочих диалектах (sqlite) collation не задаём.
    bind = op.get_bind()
    tag_collation = "utf8mb4_bin" if bind.engine.name == "mysql" else None

    op.create_table(
        "node_inbounds",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("inbound_tag", sa.String(length=256, collation=tag_collation), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inbound_tag"], ["inbounds.tag"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "inbound_tag"),
    )


def downgrade() -> None:
    op.drop_table("node_inbounds")
