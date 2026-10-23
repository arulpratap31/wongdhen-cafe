"""V26 shift handover and service-issue tables (additive, safe for older databases).

Revision ID: v26_0005
Revises: v24_0004
"""
from alembic import op

revision = 'v26_0005'
down_revision = 'v24_0004'
branch_labels = None
depends_on = None


def upgrade():
    from app import Base
    conn=op.get_bind()
    for name in ('v26_shift_handover', 'v26_service_issues'):
        Base.metadata.tables[name].create(bind=conn,checkfirst=True)


def downgrade():
    # Avoid irreversible loss of staff operational records during release rollback.
    pass
