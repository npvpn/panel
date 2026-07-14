"""merge heads 1598 and 1657

Revision ID: c17a0aab3738
Revises: 2c0cafb40725, af83ddaadbe7
Create Date: 2026-07-14 11:20:04.987025

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c17a0aab3738'
down_revision = ('2c0cafb40725', 'af83ddaadbe7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
