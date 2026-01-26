"""enforce unique proxy per (user, protocol)

Revision ID: f3a1b2c4d6e7
Revises: 2b231de97dc3
Create Date: 2026-01-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3a1b2c4d6e7'
down_revision = '2b231de97dc3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deduplicate existing proxies: keep the lowest id per (user_id, type)
    bind = op.get_bind()
    proxies = bind.execute(sa.text(
        "SELECT id, user_id, CAST(type AS TEXT) AS type "
        "FROM proxies "
        "ORDER BY user_id, type, id"
    )).fetchall()

    seen = set()
    delete_ids = []
    for row in proxies:
        key = (row.user_id, row.type)
        if key in seen:
            delete_ids.append(row.id)
        else:
            seen.add(key)

    if delete_ids:
        # Use expanding param for portability
        bind.execute(
            sa.text("DELETE FROM proxies WHERE id IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": delete_ids}
        )

    # Add unique constraint on (user_id, type)
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.create_unique_constraint('uq_proxies_user_id_type', ['user_id', 'type'])


def downgrade() -> None:
    with op.batch_alter_table('proxies') as batch_op:
        batch_op.drop_constraint('uq_proxies_user_id_type', type_='unique')

