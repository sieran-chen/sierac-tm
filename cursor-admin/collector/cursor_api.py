"""
Cursor Admin API / Analytics API 客户端
"""

import base64
import time
from datetime import date

import httpx
from config import settings


def _auth_header() -> dict:
    token = settings.cursor_api_token
    encoded = base64.b64encode(f"{token}:".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


async def get_members() -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{settings.cursor_api_url}/teams/members",
            headers=_auth_header(),
        )
        r.raise_for_status()
        return r.json().get("teamMembers", [])


async def get_daily_usage(
    start_date: date, end_date: date, page: int = 1, page_size: int = 500
) -> dict:
    start_ms = int(time.mktime(start_date.timetuple()) * 1000)
    end_ms = int(time.mktime(end_date.timetuple()) * 1000)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{settings.cursor_api_url}/teams/daily-usage-data",
            headers={**_auth_header(), "Content-Type": "application/json"},
            json={"startDate": start_ms, "endDate": end_ms, "page": page, "pageSize": page_size},
        )
        r.raise_for_status()
        return r.json()


async def get_spend(page: int = 1, page_size: int = 500) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{settings.cursor_api_url}/teams/spend",
            headers={**_auth_header(), "Content-Type": "application/json"},
            json={"page": page, "pageSize": page_size},
        )
        r.raise_for_status()
        return r.json()


async def get_usage_events(
    email: str, start_ms: int, end_ms: int, page: int = 1, page_size: int = 200
) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{settings.cursor_api_url}/teams/filtered-usage-events",
            headers={**_auth_header(), "Content-Type": "application/json"},
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
