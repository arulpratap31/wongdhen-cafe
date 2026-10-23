"""Alembic configuration for Wongdhen's existing SQLAlchemy metadata.

Existing V8 application modules currently bootstrap their own tables on import.
This is a baseline-adoption migration, not a refactor of the legacy bootstrap.
"""
from alembic import context
from sqlalchemy import pool, create_engine
from app import Base, DB_URL

config = context.config
target_metadata = Base.metadata

def offline():
    context.configure(url=DB_URL, target_metadata=target_metadata, literal_binds=True, dialect_opts={'paramstyle':'named'})
    with context.begin_transaction():context.run_migrations()

def online():
    engine=create_engine(DB_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():context.run_migrations()
    engine.dispose()

if context.is_offline_mode():offline()
else:online()
