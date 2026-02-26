"""
Shared fixtures for collector tests.
Uses mocks for DB and Cursor API so tests do not require real PostgreSQL or Cursor.
"""
import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure collector root is on path so "main", "database", etc. can be imported
_collector_root = Path(__file__).resolve().parent.parent
if str(_collector_root) not in sys.path:
    sys.path.insert(0, str(_collector_root))


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_pool():
    """Mock asyncpg pool: acquire() returns a context manager yielding a mock conn."""
    mock_conn = MagicMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.fetchval = AsyncMock(return_value=0)
    mock_conn.execute = AsyncMock(return_value=None)

    class AsyncCtx:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, *args):
            pass

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=AsyncCtx())
    return pool, mock_conn


@pytest.fixture
def app_with_mocked_db(mock_pool):
    """FastAPI app with init_db, run_full_sync, and get_pool mocked for testing."""
    pool, _ = mock_pool

    async def mock_init_db():
        pass

    async def mock_get_pool():
        return pool

    with (
        patch("main.init_db", AsyncMock(side_effect=mock_init_db)),
        patch("main.run_full_sync", AsyncMock(return_value=None)),
        patch("main.get_pool", AsyncMock(side_effect=mock_get_pool)),
    ):
        from main import app
        yield app


@pytest.fixture
def api_key():
    """Default internal API key from config (tests use same as main when not overridden)."""
    from config import settings
    return settings.internal_api_key
