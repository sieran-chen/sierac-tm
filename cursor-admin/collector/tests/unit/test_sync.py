"""
Unit tests for sync module: sync_members, sync_daily_usage, sync_spend.
Mocks cursor_api and database.get_pool.
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sync import sync_daily_usage, sync_members, sync_spend


@pytest.mark.asyncio
async def test_sync_members_calls_api_and_executes_upsert():
    mock_members = [
        {"id": 1, "email": "a@b.com", "name": "A", "role": "member", "isRemoved": False},
    ]
    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_pool = MagicMock()

    class AsyncCtx:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, *args):
            pass

    mock_pool.acquire = MagicMock(return_value=AsyncCtx())

    with (
        patch("sync.get_members", AsyncMock(return_value=mock_members)),
        patch("sync.get_pool", AsyncMock(return_value=mock_pool)),
    ):
        await sync_members()

    assert mock_conn.execute.await_count == 1
    call_args = mock_conn.execute.await_args
    assert "INSERT INTO members" in call_args[0][0]
    assert "ON CONFLICT (email)" in call_args[0][0]
    assert call_args[0][1] == "1"
    assert call_args[0][2] == "a@b.com"


@pytest.mark.asyncio
async def test_sync_daily_usage_stops_when_no_data():
    with (
        patch("sync.get_daily_usage", AsyncMock(return_value={"data": []})),
        patch("sync.get_pool") as mock_get_pool,
    ):
        await sync_daily_usage(days_back=1)

    mock_get_pool.return_value.acquire.assert_not_called()


@pytest.mark.asyncio
async def test_sync_daily_usage_writes_rows_when_data_returned():
    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_pool = MagicMock()

    class AsyncCtx:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, *args):
            pass

    mock_pool.acquire = MagicMock(return_value=AsyncCtx())
    one_row = {
        "email": "u@x.com",
        "day": "2026-02-25",
        "agentRequests": 10,
        "chatRequests": 5,
        "composerRequests": 2,
        "totalTabsAccepted": 100,
        "totalTabsShown": 120,
        "totalLinesAdded": 50,
        "totalLinesDeleted": 10,
        "acceptedLinesAdded": 40,
        "subscriptionIncludedReqs": 80,
        "usageBasedReqs": 3,
        "mostUsedModel": "gpt-4",
        "clientVersion": "0.42",
        "isActive": True,
    }

    with (
        patch("sync.get_daily_usage", AsyncMock(return_value={"data": [one_row]})),
        patch("sync.get_pool", AsyncMock(return_value=mock_pool)),
    ):
        await sync_daily_usage(days_back=1)

    assert mock_conn.execute.await_count >= 1
    call_args = mock_conn.execute.await_args
    assert "daily_usage" in call_args[0][0]
    assert call_args[0][1] == "u@x.com"


@pytest.mark.asyncio
async def test_sync_spend_calls_api_and_executes_upsert():
    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock(return_value=None)
    mock_pool = MagicMock()

    class AsyncCtx:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, *args):
            pass

    mock_pool.acquire = MagicMock(return_value=AsyncCtx())
    spend_response = {
        "teamMemberSpend": [
            {"email": "a@b.com", "spendCents": 1000, "fastPremiumRequests": 50, "monthlyLimitDollars": 200},
        ],
        "subscriptionCycleStart": 1706745600000,
    }

    with (
        patch("sync.get_spend", AsyncMock(return_value=spend_response)),
        patch("sync.get_pool", AsyncMock(return_value=mock_pool)),
    ):
        await sync_spend()

    assert mock_conn.execute.await_count >= 1
    call_args = mock_conn.execute.await_args
    assert "spend_snapshots" in call_args[0][0]
