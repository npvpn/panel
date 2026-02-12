"""add subscription_token to users

Revision ID: b123456789ab
Revises: 4b3c9d1a2f6e
Create Date: 2026-02-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b123456789ab'
down_revision = '4b3c9d1a2f6e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('subscription_token', sa.String(length=256), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('subscription_token')

