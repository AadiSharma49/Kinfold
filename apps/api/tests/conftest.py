from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
import redis as redis_lib
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from alembic import command
from kinfold_api.config import get_settings
from kinfold_api.db import get_db
from kinfold_api.deps import get_redis
from kinfold_api.main import app

settings = get_settings()

API_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def _migrated_test_db() -> None:
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", settings.TEST_DATABASE_URL)
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def engine():
    return create_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True)


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    """Each test runs inside an outer transaction that's rolled back at the
    end, so tables are effectively reset per test without re-running
    migrations. The session joins that transaction via a SAVEPOINT, so a
    rollback inside the test (e.g. after an expected DB error) only undoes
    back to the savepoint, not the whole test's data."""
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)

    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture()
def test_redis() -> Generator[redis_lib.Redis, None, None]:
    client = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    client.flushdb()
    try:
        yield client
    finally:
        client.flushdb()
        client.close()


@pytest.fixture()
def client(db_session: Session, test_redis: redis_lib.Redis) -> Generator[TestClient, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    def _override_get_redis() -> Generator[redis_lib.Redis, None, None]:
        yield test_redis

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
