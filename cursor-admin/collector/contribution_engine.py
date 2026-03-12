"""
Contribution score engine (v3.0): aggregate ai_code_commits, apply incentive formula
(incentive_pool * contribution_pct * delivery_factor), upsert contribution_scores and leaderboard_snapshots.

Data source: ai_code_commits (tab_lines_added + composer_lines_added = ai_lines).
No Hook, no agent_sessions, no git_contributions dependency.
"""

import calendar
import json
import logging
from datetime import date, timedelta

from database import get_pool

log = logging.getLogger("contribution_engine")


def period_key_to_date_range(period_type: str, period_key: str) -> tuple[date, date] | None:
    """Return (start_date, end_date) inclusive for the given period. Returns None if invalid."""
    if period_type == "daily":
        try:
            d = date.fromisoformat(period_key)
            return d, d
        except ValueError:
            return None
    if period_type == "weekly":
        try:
            parts = period_key.split("-W")
            if len(parts) != 2:
                return None
            year, week = int(parts[0]), int(parts[1])
            return date.fromisocalendar(year, week, 1), date.fromisocalendar(year, week, 7)
        except (ValueError, IndexError):
            return None
    if period_type == "monthly":
        try:
            parts = period_key.split("-")
            if len(parts) != 2:
                return None
            year, month = int(parts[0]), int(parts[1])
            _, last = calendar.monthrange(year, month)
            return date(year, month, 1), date(year, month, last)
        except (ValueError, IndexError):
            return None
    return None


async def _aggregate_ai_commits(
    pool, period_type: str, period_key: str
) -> dict[tuple[str, int | None], dict]:
    """
    Aggregate ai_code_commits by (user_email, project_id) for the given period.
    Returns dict key -> {ai_lines_added, total_lines_added, commit_count}.
    """
    rng = period_key_to_date_range(period_type, period_key)
    if not rng:
        return {}
    start_d, end_d = rng
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT user_email, project_id,
                   COALESCE(SUM(tab_lines_added + composer_lines_added), 0)::int AS ai_lines_added,
                   COALESCE(SUM(total_lines_added), 0)::int AS total_lines_added,
                   COUNT(DISTINCT commit_hash)::int AS commit_count
            FROM ai_code_commits
            WHERE commit_ts >= $1 AND commit_ts < ($2::date + INTERVAL '1 day')
            GROUP BY user_email, project_id
            """,
            start_d,
            end_d,
        )
    out: dict[tuple[str, int | None], dict] = {}
    for r in rows:
        key = (r["user_email"], r["project_id"])
        out[key] = {
            "ai_lines_added": r["ai_lines_added"],
            "total_lines_added": r["total_lines_added"],
            "commit_count": r["commit_count"],
        }
    return out


async def calculate_period(period_type: str, period_key: str, rule_id: int = 1) -> None:
    """
    1. Aggregate ai_code_commits for period.
    2. For each project: compute contribution_pct = member_ai / project_total_ai.
    3. incentive_amount = project.incentive_pool * contribution_pct * delivery_factor (default 1.0).
    4. Upsert contribution_scores per (user_email, project_id).
    5. Upsert aggregate row (project_id=NULL) per user.
    6. Rank by ai_lines_added DESC (all users, no hook filter).
    7. Save leaderboard_snapshot.
    """
    pool = await get_pool()
    data = await _aggregate_ai_commits(pool, period_type, period_key)
    if not data:
        log.info("No ai_code_commits data for %s %s", period_type, period_key)
        return

    # Load projects for incentive_pool and delivery_factor
    async with pool.acquire() as conn:
        proj_rows = await conn.fetch(
            "SELECT id, incentive_pool FROM projects WHERE status = 'active'"
        )
    project_pools: dict[int, float] = {r["id"]: float(r["incentive_pool"] or 0) for r in proj_rows}

    # Per-project totals (for contribution_pct)
    project_totals: dict[int, int] = {}
    for (user_email, project_id), vals in data.items():
        if project_id is not None:
            project_totals[project_id] = project_totals.get(project_id, 0) + vals["ai_lines_added"]

    # Upsert per-project rows
    for (user_email, project_id), vals in data.items():
        if project_id is None:
            continue
        ai = vals["ai_lines_added"]
        total_l = vals["total_lines_added"]
        commits = vals["commit_count"]
        proj_total = project_totals.get(project_id, 0)
        contribution_pct = round(ai / proj_total, 6) if proj_total else 0.0
        ai_ratio = round(ai / total_l, 4) if total_l else 0.0
        pool_amount = project_pools.get(project_id, 0.0)
        incentive_amount = round(pool_amount * contribution_pct, 2)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO contribution_scores (
                    user_email, project_id, period_type, period_key, rule_id,
                    ai_lines_added, total_lines_added, commit_count,
                    ai_ratio, contribution_pct, delivery_factor, incentive_amount, rank
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,1.0,$11,NULL)
                ON CONFLICT (user_email, project_id, period_type, period_key) DO UPDATE SET
                    rule_id = EXCLUDED.rule_id,
                    ai_lines_added = EXCLUDED.ai_lines_added,
                    total_lines_added = EXCLUDED.total_lines_added,
                    commit_count = EXCLUDED.commit_count,
                    ai_ratio = EXCLUDED.ai_ratio,
                    contribution_pct = EXCLUDED.contribution_pct,
                    incentive_amount = EXCLUDED.incentive_amount,
                    rank = NULL
                """,
                user_email, project_id, period_type, period_key, rule_id,
                ai, total_l, commits, ai_ratio, contribution_pct, incentive_amount,
            )

    # Aggregate per user (project_id=NULL): sum across projects
    user_agg: dict[str, dict] = {}
    for (user_email, project_id), vals in data.items():
        if user_email not in user_agg:
            user_agg[user_email] = {"ai_lines_added": 0, "total_lines_added": 0,
                                    "commit_count": 0, "incentive_amount": 0.0}
        user_agg[user_email]["ai_lines_added"] += vals["ai_lines_added"]
        user_agg[user_email]["total_lines_added"] += vals["total_lines_added"]
        user_agg[user_email]["commit_count"] += vals["commit_count"]
        if project_id is not None:
            proj_total = project_totals.get(project_id, 0)
            contribution_pct = vals["ai_lines_added"] / proj_total if proj_total else 0.0
            pool_amount = project_pools.get(project_id, 0.0)
            user_agg[user_email]["incentive_amount"] += pool_amount * contribution_pct

    for user_email, agg in user_agg.items():
        ai = agg["ai_lines_added"]
        total_l = agg["total_lines_added"]
        incentive = round(agg["incentive_amount"], 2)
        ai_ratio = round(ai / total_l, 4) if total_l else 0.0
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO contribution_scores (
                    user_email, project_id, period_type, period_key, rule_id,
                    ai_lines_added, total_lines_added, commit_count,
                    ai_ratio, contribution_pct, delivery_factor, incentive_amount, rank
                ) VALUES ($1,NULL,$2,$3,$4,$5,$6,$7,$8,0,1.0,$9,NULL)
                ON CONFLICT (user_email, project_id, period_type, period_key) DO UPDATE SET
                    rule_id = EXCLUDED.rule_id,
                    ai_lines_added = EXCLUDED.ai_lines_added,
                    total_lines_added = EXCLUDED.total_lines_added,
                    commit_count = EXCLUDED.commit_count,
                    ai_ratio = EXCLUDED.ai_ratio,
                    incentive_amount = EXCLUDED.incentive_amount,
                    rank = NULL
                """,
                user_email, period_type, period_key, rule_id,
                ai, total_l, agg["commit_count"], ai_ratio, incentive,
            )

    # Rank all users by ai_lines_added DESC (aggregate rows)
    async with pool.acquire() as conn:
        ranked = await conn.fetch(
            """
            SELECT user_email, ai_lines_added
            FROM contribution_scores
            WHERE period_type=$1 AND period_key=$2 AND project_id IS NULL
            ORDER BY ai_lines_added DESC
            """,
            period_type, period_key,
        )
    for rank, row in enumerate(ranked, start=1):
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE contribution_scores SET rank=$1
                WHERE user_email=$2 AND project_id IS NULL AND period_type=$3 AND period_key=$4
                """,
                rank, row["user_email"], period_type, period_key,
            )

    # Leaderboard snapshot
    snapshot_entries = [
        {
            "rank": i + 1,
            "user_email": r["user_email"],
            "ai_lines_added": r["ai_lines_added"],
        }
        for i, r in enumerate(ranked)
    ]
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO leaderboard_snapshots (period_type, period_key, snapshot)
            VALUES ($1,$2,$3)
            ON CONFLICT (period_type, period_key) DO UPDATE SET snapshot=EXCLUDED.snapshot, created_at=NOW()
            """,
            period_type, period_key,
            json.dumps({"entries": snapshot_entries}),
        )
    log.info("Calculated %s %s: %d users", period_type, period_key, len(user_agg))


async def run_calculate_latest(period_type: str, rule_id: int = 1) -> None:
    """Compute both the latest completed period and the current in-progress period."""
    today = date.today()
    keys: list[str] = []
    if period_type == "daily":
        keys = [(today - timedelta(days=1)).isoformat(), today.isoformat()]
    elif period_type == "weekly":
        last_week = today - timedelta(days=7)
        y_prev, w_prev, _ = last_week.isocalendar()
        y_cur, w_cur, _ = today.isocalendar()
        keys = [f"{y_prev}-W{w_prev:02d}", f"{y_cur}-W{w_cur:02d}"]
    elif period_type == "monthly":
        first_this = today.replace(day=1)
        last_month = first_this - timedelta(days=1)
        keys = [last_month.strftime("%Y-%m"), today.strftime("%Y-%m")]
    else:
        log.warning("Unknown period_type %s", period_type)
        return
    for period_key in keys:
        await calculate_period(period_type, period_key, rule_id)
