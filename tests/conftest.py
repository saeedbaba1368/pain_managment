"""
Shared pytest fixtures.

config.py's Settings() is instantiated at import time (module-level
`settings = get_settings()`), so every required env var must exist
*before* anything imports `config` -- including transitively, e.g.
`core.security` -> `config`. We set them here, in conftest.py, which
pytest always imports before collecting any test module.

DATABASE_URL points at a real Postgres. Tests that need a live database
depend on the `require_db` fixture below and are skipped automatically
if that Postgres isn't reachable (e.g. this review sandbox, or CI
without `docker compose up db`). Everything else here -- security
primitives, i18n, schema validation, RBAC decision logic -- runs with
no database at all.
"""
from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-32chars")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production-32ch")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "Zm9vYmFyYmF6cXV4Zm9vYmFyYmF6cXV4Zm9vYmFyYmE=")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_pain_dashboard")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DEBUG", "true")

import pytest
from sqlalchemy.exc import OperationalError


@pytest.fixture(scope="session")
def require_db():
    """Skip the test if the configured Postgres isn't reachable."""
    from config import settings
    from sqlalchemy import create_engine

    try:
        engine = create_engine(str(settings.DATABASE_URL))
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("No Postgres reachable at DATABASE_URL -- start it with `docker compose up -d db`.")
