"""user sub_support_url and sub_profile_title

Revision ID: a1c2e3f4b5d6
Revises: b123456789ab
Create Date: 2026-03-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1c2e3f4b5d6'
down_revision = 'b123456789ab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('sub_support_url', sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column('sub_profile_title', sa.String(length=256), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('sub_profile_title')
        batch_op.drop_column('sub_support_url')
