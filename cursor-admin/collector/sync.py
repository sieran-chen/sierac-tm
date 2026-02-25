"""
定时同步任务：从 Cursor Admin API 拉取用量与支出，写入 PostgreSQL
"""

import logging
from datetime import date, timedelta

from cursor_api import get_members, get_daily_usage, get_spend
from database import get_pool

log = logging.getLogger("sync")


async def sync_members():
    members = await get_members()
    pool = await get_pool()
    async with pool.acquire() as conn:
        for m in members:
            await conn.execute(
                """
                INSERT INTO members (user_id, email, name, role, is_removed)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (email) DO UPDATE SET
                    user_id    = EXCLUDED.user_id,
                    name       = EXCLUDED.name,
                    role       = EXCLUDED.role,
                    is_removed = EXCLUDED.is_removed,
                    synced_at  = NOW()
                """,
                str(m.get("id", "")),
                m.get("email", ""),
                m.get("name", ""),
                m.get("role", "member"),
                bool(m.get("isRemoved", False)),
            )
    log.info("Synced %d members", len(members))


async def sync_daily_usage(days_back: int = 2):
    """拉取最近 N 天的用量（每小时一次，days_back=2 保证不漏数据）"""
    end = date.today()
    start = end - timedelta(days=days_back)
    page, page_size = 1, 500
    total_rows = 0
    pool = await get_pool()

    while True:
        data = await get_daily_usage(start, end, page=page, page_size=page_size)
        rows = data.get("data", [])
        if not rows:
            break

        async with pool.acquire() as conn:
            for row in rows:
                await conn.execute(
                    """
                    INSERT INTO daily_usage (
                        email, day, agent_requests, chat_requests, composer_requests,
                        total_tabs_accepted, total_tabs_shown,
                        total_lines_added, total_lines_deleted, accepted_lines_added,
                        subscription_reqs, usage_based_reqs,
                        most_used_model, client_version, is_active
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                    ON CONFLICT (email, day) DO UPDATE SET
                        agent_requests       = EXCLUDED.agent_requests,
                        chat_requests        = EXCLUDED.chat_requests,
                        composer_requests    = EXCLUDED.composer_requests,
                        total_tabs_accepted  = EXCLUDED.total_tabs_accepted,
                        total_tabs_shown     = EXCLUDED.total_tabs_shown,
                        total_lines_added    = EXCLUDED.total_lines_added,
                        total_lines_deleted  = EXCLUDED.total_lines_deleted,
                        accepted_lines_added = EXCLUDED.accepted_lines_added,
                        subscription_reqs    = EXCLUDED.subscription_reqs,
                        usage_based_reqs     = EXCLUDED.usage_based_reqs,
                        most_used_model      = EXCLUDED.most_used_model,
                        client_version       = EXCLUDED.client_version,
                        is_active            = EXCLUDED.is_active,
                        synced_at            = NOW()
                    """,
                    row.get("email", ""),
                    row.get("day"),
                    row.get("agentRequests", 0),
                    row.get("chatRequests", 0),
                    row.get("composerRequests", 0),
                    row.get("totalTabsAccepted", 0),
                    row.get("totalTabsShown", 0),
                    row.get("totalLinesAdded", 0),
                    row.get("totalLinesDeleted", 0),
                    row.get("acceptedLinesAdded", 0),
                    row.get("subscriptionIncludedReqs", 0),
                    row.get("usageBasedReqs", 0),
                    row.get("mostUsedModel"),
                    row.get("clientVersion"),
                    bool(row.get("isActive", False)),
                )
        total_rows += len(rows)

        pagination = data.get("pagination", {})
        if not pagination.get("hasNextPage"):
            break
        page += 1

    log.info("Synced %d daily-usage rows (last %d days)", total_rows, days_back)


async def sync_spend():
    data = await get_spend(page=1, page_size=500)
    members = data.get("teamMemberSpend", [])
    cycle_start_ms = data.get("subscriptionCycleStart", 0)
    from datetime import datetime

    cycle_start = (
        datetime.utcfromtimestamp(cycle_start_ms / 1000).date()
        if cycle_start_ms
        else date.today().replace(day=1)
    )

    pool = await get_pool()
    async with pool.acquire() as conn:
        for m in members:
            await conn.execute(
                """
                INSERT INTO spend_snapshots (email, billing_cycle_start, spend_cents, fast_premium_requests, monthly_limit_dollars)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (email, billing_cycle_start) DO UPDATE SET
                    spend_cents           = EXCLUDED.spend_cents,
                    fast_premium_requests = EXCLUDED.fast_premium_requests,
                    monthly_limit_dollars = EXCLUDED.monthly_limit_dollars,
                    synced_at             = NOW()
                """,
                m.get("email", ""),
                cycle_start,
                m.get("spendCents", 0),
                m.get("fastPremiumRequests", 0),
                m.get("monthlyLimitDollars"),
            )
    log.info("Synced spend for %d members (cycle start %s)", len(members), cycle_start)


async def run_full_sync():
    """完整同步：成员 → 用量 → 支出"""
    try:
        await sync_members()
    except Exception as e:
        log.error("sync_members failed: %s", e)
    try:
        await sync_daily_usage(days_back=2)
    except Exception as e:
        log.error("sync_daily_usage failed: %s", e)
    try:
        await sync_spend()
    except Exception as e:
        log.error("sync_spend failed: %s", e)
