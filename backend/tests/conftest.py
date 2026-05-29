"""Pytest configuration — always use an isolated test database, never dev."""

from __future__ import annotations

import os

# Must run before app.database / settings are imported.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://culturegraph:culturegraph@localhost:5432/culturegraph_test",
)
os.environ.setdefault("VISUAL_EMBEDDING_BACKEND", "test")

from collections.abc import Generator, Iterator

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 — register models on Base.metadata
from app.auth.jwt import create_access_token
from app.config import settings
from app.database import Base, get_db
from app.main import app


def _ensure_database(url: str) -> None:
    parsed = make_url(url)
    db_name = parsed.database
    if not db_name:
        return

    probe = create_engine(url)
    try:
        with probe.connect() as conn:
            conn.execute(text("SELECT 1"))
        return
    except Exception:
        pass
    finally:
        probe.dispose()

    admin_engine = create_engine(
        parsed.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    except Exception as exc:
        raise RuntimeError(
            f"Test database {db_name!r} is missing and could not be created automatically. "
            "Create it once (see README Testing), or set TEST_DATABASE_URL to an existing database."
        ) from exc
    finally:
        admin_engine.dispose()


class _TestingSessionMaker:
    """Session factory that wraps each commit in a nested savepoint."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory
        event.listen(factory, "after_transaction_end", self._restart_savepoint)

    def __call__(self) -> Session:
        session = self._factory()
        session.begin_nested()
        return session

    @staticmethod
    def _restart_savepoint(session: Session, transaction) -> None:
        parent = transaction._parent
        if transaction.nested and parent is not None and not parent.nested:
            session.begin_nested()


@pytest.fixture(scope="session")
def test_engine():
    _ensure_database(settings.database_url)
    engine = create_engine(settings.database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_connection(test_engine) -> Generator:
    connection = test_engine.connect()
    transaction = connection.begin()
    yield connection
    transaction.rollback()
    connection.close()


@pytest.fixture
def db_session(db_connection) -> Generator[Session, None, None]:
    factory = sessionmaker(autocommit=False, autoflush=False, bind=db_connection)
    session = _TestingSessionMaker(factory)()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def isolated_test_database(db_connection, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Route API handlers and SessionLocal through rolled-back savepoints."""
    factory = sessionmaker(autocommit=False, autoflush=False, bind=db_connection)
    testing_session_local = _TestingSessionMaker(factory)

    def override_get_db() -> Generator[Session, None, None]:
        session = testing_session_local()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.database.SessionLocal", testing_session_local)
    monkeypatch.setattr("app.database.engine", db_connection)
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def configure_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "test-jwt-secret")
    monkeypatch.setattr(settings, "google_client_id", "test-google-client-id")
    monkeypatch.setattr(settings, "admin_emails", "admin@example.com,editor@example.com")


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token("admin@example.com")
    return {"Authorization": f"Bearer {token}"}
