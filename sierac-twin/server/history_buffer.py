"""Ring buffer for telemetry history. Keeps last 24h of (timestamp, point_id, value)."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any


class HistoryBuffer:
    def __init__(self, max_seconds: int = 86400) -> None:
        self._buffer: deque[tuple[datetime, str, float]] = deque()
        self._max_seconds = max_seconds

    def append(self, point_id: str, value: float, ts: datetime | None = None) -> None:
        if ts is None:
            ts = datetime.now(timezone.utc)
        self._buffer.append((ts, point_id, value))
        self._trim()

    def query(
        self,
        point_id: str,
        hours: float,
        interval_seconds: int = 10,
    ) -> list[dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        points = [
            (ts, val)
            for ts, pid, val in self._buffer
            if pid == point_id and ts >= cutoff
        ]
        points.sort(key=lambda x: x[0])
        if interval_seconds <= 0:
            return [{"timestamp": ts.isoformat(), "value": val} for ts, val in points]
        out: list[dict[str, Any]] = []
        last_ts: datetime | None = None
        for ts, val in points:
            if last_ts is None or (ts - last_ts).total_seconds() >= interval_seconds:
                out.append({"timestamp": ts.isoformat(), "value": val})
                last_ts = ts
        return out

    def _trim(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._max_seconds)
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()
