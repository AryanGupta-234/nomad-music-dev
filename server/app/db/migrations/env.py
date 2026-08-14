from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.db.models import Base
from app.config.settings import get_settings

config = context.config
if config.config_file_name:
    try:
        fileConfig(config.config_file_name)
    except (KeyError, ValueError):
        pass
target_metadata = Base.metadata

def run_migrations_offline():
    url = get_settings().database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = get_settings().database_url
    connectable = create_engine(url, poolclass=pool.NullPool, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
