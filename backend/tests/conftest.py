"""Shared test setup.

Tests run against a real Postgres database whose schema comes from the Alembic
migration (never create_all). Point TEST_DATABASE_URL at a throwaway database
whose name ends in "_test"; the schema is dropped and rebuilt on every run:

    TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/briefbase_test pytest
"""

import os
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

_test_url = os.environ.get("TEST_DATABASE_URL", "")
if not _test_url or not (make_url(_test_url).database or "").endswith("_test"):
    # Guard: the fixtures below wipe the database, so never touch a real one.
    pytest.exit("Set TEST_DATABASE_URL to a database whose name ends in '_test'", returncode=2)

# Must be set before the app is imported: settings are read at import time.
# Real environment variables take priority over the root .env file.
os.environ["DATABASE_URL"] = _test_url
os.environ["JWT_SECRET"] = "test-only-jwt-secret-0123456789abcdef"
os.environ["GEMINI_API_KEY"] = ""  # the real Gemini API is never called from tests

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    # downgrade + upgrade also proves the migration is reversible.
    cfg = Config(str(ALEMBIC_INI))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE notes, users RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def register(client):
    """Register a user and return Authorization headers for them."""

    def _register(email: str = "alice@example.com", password: str = "password123") -> dict:
        r = client.post("/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _register
