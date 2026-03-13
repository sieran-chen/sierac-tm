"""Tests for HistoryBuffer: append, query, trim, interval sampling."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from history_buffer import HistoryBuffer


def test_append_and_query() -> None:
    buf = HistoryBuffer(max_seconds=3600)
    now = datetime.now(timezone.utc)
    buf.append("speed", 450.0, now)
    buf.append("speed", 451.0, now)
    buf.append("temperature", 4.5, now)
    result = buf.query("speed", hours=1, interval_seconds=0)
    assert len(result) == 2
    assert result[0]["value"] == 450.0
    assert result[1]["value"] == 451.0
    result_t = buf.query("temperature", hours=1, interval_seconds=0)
    assert len(result_t) == 1
    assert result_t[0]["value"] == 4.5


def test_trim_old_data() -> None:
    buf = HistoryBuffer(max_seconds=2)
    base = datetime.now(timezone.utc)
    buf.append("speed", 100.0, base - timedelta(seconds=5))
    buf.append("speed", 200.0, base - timedelta(seconds=3))
    buf.append("speed", 300.0, base)
    result = buf.query("speed", hours=1, interval_seconds=0)
    assert len(result) >= 1
    assert result[-1]["value"] == 300.0


def test_query_empty() -> None:
    buf = HistoryBuffer(max_seconds=3600)
    result = buf.query("unknown_point", hours=1)
    assert result == []


def test_interval_sampling() -> None:
    buf = HistoryBuffer(max_seconds=3600)
    base = datetime.now(timezone.utc)
    for i in range(20):
        buf.append("speed", 450.0 + i, base + timedelta(seconds=i))
    result = buf.query("speed", hours=1, interval_seconds=5)
    assert len(result) <= 5
    assert all("timestamp" in r and "value" in r for r in result)
