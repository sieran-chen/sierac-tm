"""
Cursor Admin API 客户端（官方 Basic Auth：key 为 username，密码为空）
"""

import logging
import time
from datetime import date

import httpx
from config import settings

log = logging.getLogger("cursor_api")


def _auth():
    token = settings.get_cursor_token()
    if not token:
        return None
    return httpx.BasicAuth(token, "")


async def _request(method: str, url: str, **kwargs) -> httpx.Response:
    auth = _auth()
    if not auth:
        raise ValueError("CURSOR_API_TOKEN 未配置")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.request(method, url, auth=auth, **kwargs)
        if r.status_code == 401:
            log.warning("Cursor API 401: url=%s body=%s", url, r.text[:500] if r.text else "")
        return r


async def get_members() -> list[dict]:
    r = await _request("GET", f"{settings.cursor_api_url}/teams/members")
    r.raise_for_status()
    return r.json().get("teamMembers", [])


async def get_daily_usage(
    start_date: date, end_date: date, page: int = 1, page_size: int = 500
) -> dict:
    start_ms = int(time.mktime(start_date.timetuple()) * 1000)
    end_ms = int(time.mktime(end_date.timetuple()) * 1000)
    r = await _request(
        "POST",
        f"{settings.cursor_api_url}/teams/daily-usage-data",
        headers={"Content-Type": "application/json"},
        json={"startDate": start_ms, "endDate": end_ms, "page": page, "pageSize": page_size},
    )
    r.raise_for_status()
    return r.json()


async def get_spend(page: int = 1, page_size: int = 500) -> dict:
    r = await _request(
        "POST",
        f"{settings.cursor_api_url}/teams/spend",
        headers={"Content-Type": "application/json"},
        json={"page": page, "pageSize": page_size},
    )
    r.raise_for_status()
    return r.json()


async def get_usage_events(
    email: str, start_ms: int, end_ms: int, page: int = 1, page_size: int = 200
) -> dict:
    r = await _request(
        "POST",
        f"{settings.cursor_api_url}/teams/filtered-usage-events",
        headers={"Content-Type": "application/json"},
        json={
            "email": email,
            "startDate": start_ms,
            "endDate": end_ms,
            "page": page,
            "pageSize": page_size,
        },
    )
    r.raise_for_status()
    return r.json()
