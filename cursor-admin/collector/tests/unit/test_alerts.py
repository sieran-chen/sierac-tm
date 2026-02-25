"""
Unit tests for alerts module: check_alerts and dispatch logic.
Mocks database.get_pool and notification functions.
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alerts import check_alerts, dispatch_alert


@pytest.mark.asyncio
async def test_check_alerts_does_not_trigger_when_no_rules():
    mock_conn = MagicMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_pool = MagicMock()

    class AsyncCtx:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, *args):
            pass

    mock_pool.acquire = MagicMock(return_value=AsyncCtx())

    with patch("alerts.get_pool", AsyncMock(return_value=mock_pool)):
        await check_alerts()

    mock_conn.fetch.assert_called()
    first_call = mock_conn.fetch.call_args_list[0]
    assert "alert_rules" in first_call[0][0] or "SELECT" in first_call[0][0]


@pytest.mark.asyncio
async def test_check_alerts_does_not_trigger_when_value_below_threshold():
    mock_conn = MagicMock()
    mock_conn.fetch = AsyncMock(
        return_value=[
            {
                "id": 1,
                "name": "Test",
                "metric": "daily_agent_requests",
                "scope": "user",
                "target_email": "a@b.com",
                "threshold": 1000,
                "notify_channels": "[]",
                "enabled": True,
            }
        ]
    )
    mock_conn.fetchrow = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock(return_value=None)
    mock_pool = MagicMock()

    class AsyncCtx:
        async def __aenter__(self):
            return mock_conn

        async def __aexit__(self, *args):
            pass

    mock_pool.acquire = MagicMock(return_value=AsyncCtx())

    with patch("alerts.get_pool", AsyncMock(return_value=mock_pool)):
        await check_alerts()

    mock_conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_alert_calls_notify_webhook_when_channel_is_webhook():
    with patch("alerts.notify_webhook", AsyncMock()) as mock_webhook:
        await dispatch_alert(
            {"name": "R", "metric": "m", "threshold": 10, "notify_channels": [{"type": "webhook", "url": "http://x"}]},
            100.0,
            {},
        )
        mock_webhook.assert_called_once()
        assert mock_webhook.await_args[0][1].get("value") == 100.0
