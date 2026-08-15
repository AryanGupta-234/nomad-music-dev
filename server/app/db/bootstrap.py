from __future__ import annotations

from pathlib import Path
from sqlalchemy import inspect
from alembic import command
from alembic.config import Config


def _config() -> Config:
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    return cfg


def upgrade_database() -> None:
    """Bring the desktop database to the latest migration before the API starts.

    Older NOMAD builds created tables with SQLAlchemy directly and therefore may
    have no alembic_version row. Those databases are stamped at the current head
    after verifying that the legacy schema already exists. Fresh databases run the
    real migration chain from scratch.
    """
    cfg = _config()
    db_url = __import__("app.config.settings", fromlist=["get_settings"]).get_settings().database_url
    cfg.set_main_option("sqlalchemy.url", db_url.replace("%", "%%"))

    engine = __import__("app.db.session", fromlist=["engine"]).engine
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "alembic_version" in tables:
        command.upgrade(cfg, "head")
        return

    # Legacy create_all databases are already structurally populated. Stamping
    # avoids replaying CREATE TABLE migrations against an existing installation.
    legacy_markers = {"profiles", "tracks", "playlists", "player_states"}
    if legacy_markers.issubset(tables):
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")
