"""Unit tests for contribution_engine: period parsing and calculate_period with mocked DB."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from contribution_engine import period_key_to_date_range


def test_period_key_to_date_range_daily():
    start, end = period_key_to_date_range("daily", "2026-02-25")
    assert start == end == date(2026, 2, 25)
    assert period_key_to_date_range("daily", "invalid") is None


def test_period_key_to_date_range_weekly():
    start, end = period_key_to_date_range("weekly", "2026-W08")
    assert start == date(2026, 2, 16)
    assert end == date(2026, 2, 22)
    assert period_key_to_date_range("weekly", "2026-W99") is None
    assert period_key_to_date_range("weekly", "bad") is None


def test_period_key_to_date_range_monthly():
    start, end = period_key_to_date_range("monthly", "2026-02")
    assert start == date(2026, 2, 1)
    assert end == date(2026, 2, 28)
    start2, end2 = period_key_to_date_range("monthly", "2024-02")
    assert start2 == date(2024, 2, 1)
    assert end2 == date(2024, 2, 29)
    assert period_key_to_date_range("monthly", "2026-13") is None


def test_period_key_to_date_range_unknown():
    assert period_key_to_date_range("yearly", "2026") is None


@pytest.mark.asyncio
async def test_calculate_period_no_rule():
    """When no enabled rule exists, calculate_period returns without error."""
    from contribution_engine import calculate_period

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool.acquire = MagicMock(return_value=mock_ctx)

    with patch("contribution_engine.get_pool", AsyncMock(return_value=mock_pool)):
        await calculate_period("weekly", "2026-W08", rule_id=999)
    mock_conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_calculate_period_no_data():
    """When rule exists but no git/session/usage data, no contribution_scores inserted."""
    from contribution_engine import calculate_period

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "weights": {
                "lines_added": 0.35,
                "commit_count": 0.2,
                "session_duration_hours": 0.25,
                "agent_requests": 0.1,
                "files_changed": 0.1,
            },
            "caps": {},
        }
    )
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool.acquire = MagicMock(return_value=mock_ctx)

    with patch("contribution_engine.get_pool", AsyncMock(return_value=mock_pool)):
        await calculate_period("weekly", "2026-W08", rule_id=1)

    # Should have called fetch for git, sessions, usage; no execute for contribution_scores insert
    assert mock_conn.fetch.call_count >= 3
    execute_calls = [c for c in mock_conn.execute.await_args_list if c.args and "contribution_scores" in str(c.args[0])]
    assert len(execute_calls) == 0


@pytest.mark.asyncio
async def test_calculate_period_with_git_only():
    """Git data only: one per-project row and one aggregate row, hook_adopted false."""
    from contribution_engine import calculate_period

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(
        return_value={
            "id": 1,
            "weights": {
                "lines_added": 0.35,
                "commit_count": 0.2,
                "session_duration_hours": 0.25,
                "agent_requests": 0.1,
                "files_changed": 0.1,
            },
            "caps": {},
        }
    )
    # First fetch = git (one row), then sessions (empty), then usage (empty), then rank query, then snapshot
    mock_conn.fetch = AsyncMock(
        side_effect=[
            [{"project_id": 1, "user_email": "a@x.com", "lines_added": 100, "lines_removed": 10, "commit_count": 2, "files_changed": 5}],
            [],
            [],
            [],  # rank query returns empty (no hook_adopted)
        ]
    )
    mock_conn.execute = AsyncMock()
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_pool.acquire = MagicMock(return_value=mock_ctx)

    with patch("contribution_engine.get_pool", AsyncMock(return_value=mock_pool)):
        await calculate_period("weekly", "2026-W08", rule_id=1)

    # Per-project upsert + aggregate upsert + rank updates + snapshot
    assert mock_conn.execute.await_count >= 2
