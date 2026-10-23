"""Add persistent staff accounts to existing V8 schema.

Revision ID: v9_0002
Revises: v9_0001
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa
revision='v9_0002'
down_revision='v9_0001'
branch_labels=None
depends_on=None

def upgrade():
    # Idempotent adoption: legacy modules still call Base.metadata.create_all at import.
    if 'v9_staff_accounts' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('v9_staff_accounts',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('username',sa.String(90),nullable=False),
            sa.Column('password_hash',sa.String(180),nullable=False),
            sa.Column('role',sa.String(40),nullable=False),
            sa.Column('active',sa.Boolean(),nullable=False),
            sa.Column('session_version',sa.String(64),nullable=False),
            sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
        op.create_index('ix_v9_staff_accounts_username','v9_staff_accounts',['username'],unique=True)

def downgrade():
    # Staff accounts may contain authentication/audit history; do not drop automatically.
    pass
