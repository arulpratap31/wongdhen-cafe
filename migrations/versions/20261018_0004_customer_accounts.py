"""V24 customer-owned account tables, safe to apply to an existing V23 database.

Revision ID: v24_0004
Revises: v10_0003

The legacy app also creates absent tables on startup. This migration is idempotent
with those existing bootstrap conventions, and preserves existing tables and data.
"""
from alembic import op
import sqlalchemy as sa

revision = 'v24_0004'
down_revision = 'v10_0003'
branch_labels = None
depends_on = None


def upgrade():
    # Import uses application model definitions as the single schema source of truth.
    from app import Base
    connection = op.get_bind()
    for table_name in ('v24_customers', 'v24_customer_sessions', 'v24_oauth_attempts',
                       'v24_customer_preferences', 'v24_customer_favorites',
                       'v24_photo_bookmarks', 'v24_reservation_claims'):
        Base.metadata.tables[table_name].create(bind=connection, checkfirst=True)


def downgrade():
    # Avoid deleting customer data or authorization/audit links as a side effect of rollback.
    pass
