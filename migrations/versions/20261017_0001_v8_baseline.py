"""Adopt V8's preexisting tables into Alembic version tracking.

Revision ID: v9_0001
Revises:
Create Date: 2026-10-17

IMPORTANT: Existing V8 modules create their own tables using create_all. The
first revision records the baseline and will not rewrite or delete their data.
"""
from alembic import op
from sqlalchemy import inspect
revision='v9_0001'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    existing=set(inspect(op.get_bind()).get_table_names())
    required={'menu_items','v3_reservations','v3_dining_tables','v7_occasions'}
    missing=required-existing
    if missing:
        raise RuntimeError('V8 application schema is incomplete: '+', '.join(sorted(missing)))

def downgrade():
    # Do not destroy V8 customer data on downgrade. Version history only.
    pass
