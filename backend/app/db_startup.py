import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.config import settings
from app.database import engine

REQUIRED_TABLES = ("visits", "artworks", "annotations", "research_notes")


def _log(message: str) -> None:
    print(f"CultureGraph — {message}", flush=True)


def log_database_config() -> None:
    present = bool(settings.database_url and settings.database_url.strip())
    _log(f"DATABASE_URL present: {'yes' if present else 'no'}")


def run_migrations() -> None:
    _log("Migration start")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    _log("Migration end")


def verify_required_tables() -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    missing = [name for name in REQUIRED_TABLES if name not in existing]

    if missing:
        _log(f"Missing required tables: {', '.join(missing)}")
        sys.exit(1)

    _log(f"Required tables present: {', '.join(REQUIRED_TABLES)}")


def prepare_database() -> None:
    log_database_config()
    run_migrations()
    verify_required_tables()
