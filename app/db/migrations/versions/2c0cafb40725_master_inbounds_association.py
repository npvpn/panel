"""master inbounds association

Revision ID: 2c0cafb40725
Revises: a7b8c9d0e1f2
Create Date: 2026-07-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2c0cafb40725'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FK на inbounds.tag (utf8mb4_bin на MySQL). См. 5a20cee1a4e9.
    bind = op.get_bind()
    tag_collation = "utf8mb4_bin" if bind.engine.name == "mysql" else None

    op.create_table(
        "master_inbounds",
        sa.Column("inbound_tag", sa.String(length=256, collation=tag_collation), nullable=False),
        sa.ForeignKeyConstraint(["inbound_tag"], ["inbounds.tag"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("inbound_tag"),
    )


def downgrade() -> None:
    op.drop_table("master_inbounds")
