"""V10 persistent curated-photography catalog.

Revision ID: v10_0003
Revises: v9_0002
"""
from alembic import op
import sqlalchemy as sa
revision='v10_0003'
down_revision='v9_0002'
branch_labels=None
depends_on=None

def upgrade():
    if 'v10_photo_catalog' in sa.inspect(op.get_bind()).get_table_names():return
    op.create_table('v10_photo_catalog',
        sa.Column('id',sa.String(16),primary_key=True),
        sa.Column('filename',sa.String(240),nullable=False),
        sa.Column('category',sa.String(40),nullable=False),
        sa.Column('caption',sa.String(240),nullable=False),
        sa.Column('alt_text',sa.String(280),nullable=False),
        sa.Column('published',sa.Boolean(),nullable=False),
        sa.Column('featured',sa.Boolean(),nullable=False),
        sa.Column('focal_point',sa.String(24),nullable=False),
        sa.Column('display_order',sa.Integer(),nullable=False))
    op.create_index('ix_v10_photo_catalog_category','v10_photo_catalog',['category'])
    op.create_index('ix_v10_photo_catalog_published','v10_photo_catalog',['published'])

def downgrade():
    # Do not drop customer-managed curation on rollback.
    pass
