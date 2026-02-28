"""
Contribution score engine: aggregate git_contributions, agent_sessions, daily_usage,
apply incentive_rules weights/caps, upsert contribution_scores and leaderboard_snapshots.
"""

import calendar
import json
import logging
from datetime import date, timedelta
from decimal import Decimal

from database import get_pool


def _parse_jsonb(val) -> dict:
    """Parse a JSONB value that asyncpg may return as dict or str."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    try:
        return dict(val)
    except (TypeError, ValueError):
        return {}

log = logging.getLogger("contribution_engine")

# Dimension keys used in weights and raw data
DIM_LINES_ADDED = "lines_added"
DIM_COMMIT_COUNT = "commit_count"
DIM_SESSION_DURATION_HOURS = "session_duration_hours"
DIM_AGENT_REQUESTS = "agent_requests"
DIM_FILES_CHANGED = "files_changed"

CAP_SESSION_HOURS_PER_DAY = "session_duration_hours_per_day"
CAP_AGENT_REQUESTS_PER_DAY = "agent_requests_per_day"


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
            # period_key like "2026-W08"
            parts = period_key.split("-W")
            if len(parts) != 2:
                return None
            year, week = int(parts[0]), int(parts[1])
            start = date.fromisocalendar(year, week, 1)
            end = date.fromisocalendar(year, week, 7)
            return start, end
        except (ValueError, IndexError):
            return None
    if period_type == "monthly":
        try:
            # period_key like "2026-02"
            parts = period_key.split("-")
            if len(parts) != 2:
                return None
            year, month = int(parts[0]), int(parts[1])
            start = date(year, month, 1)
            _, last = calendar.monthrange(year, month)
            end = date(year, month, last)
            return start, end
        except (ValueError, IndexError):
            return None
    return None


async def _aggregate_git(pool, period_type: str, period_key: str) -> dict[tuple[str, int | None], dict]:
    """Key (user_email, project_id). project_id is never None (we only have per-project git data)."""
    rng = period_key_to_date_range(period_type, period_key)
    if not rng:
        return {}
    start_d, end_d = rng
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT project_id, author_email AS user_email,
                   COALESCE(SUM(lines_added), 0)::int AS lines_added,
                   COALESCE(SUM(lines_removed), 0)::int AS lines_removed,
                   COALESCE(SUM(commit_count), 0)::int AS commit_count,
                   COALESCE(SUM(files_changed), 0)::int AS files_changed
            FROM git_contributions
            WHERE commit_date >= $1 AND commit_date <= $2
            GROUP BY project_id, author_email
            """,
            start_d,
            end_d,
        )
    out: dict[tuple[str, int | None], dict] = {}
    for r in rows:
        key = (r["user_email"], r["project_id"])
        out[key] = {
            DIM_LINES_ADDED: r["lines_added"],
            "lines_removed": r["lines_removed"],
            DIM_COMMIT_COUNT: r["commit_count"],
            DIM_FILES_CHANGED: r["files_changed"],
            DIM_SESSION_DURATION_HOURS: 0,
            DIM_AGENT_REQUESTS: 0,
        }
    return out


async def _aggregate_sessions(pool, period_type: str, period_key: str, caps: dict) -> dict[tuple[str, int | None], dict]:
    """Key (user_email, project_id). Session duration capped per day (cap key session_duration_hours_per_day)."""
    rng = period_key_to_date_range(period_type, period_key)
    if not rng:
        return {}
    start_d, end_d = rng
    cap_hours = caps.get(CAP_SESSION_HOURS_PER_DAY)
    if cap_hours is None:
        cap_hours = 12
    cap_seconds_per_day = int(float(cap_hours) * 3600)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT user_email, project_id, (ended_at::date) AS d,
                   COALESCE(SUM(duration_seconds), 0)::bigint AS sec
            FROM agent_sessions
            WHERE ended_at::date >= $1 AND ended_at::date <= $2 AND project_id IS NOT NULL
            GROUP BY user_email, project_id, (ended_at::date)
            """,
            start_d,
            end_d,
        )
    # Per (user_email, project_id, day) we have sec. Cap each day then sum.
    by_key_day: dict[tuple[str, int], dict[str, int]] = {}
    for r in rows:
        key = (r["user_email"], r["project_id"])
        d = r["d"]
        sec = min(int(r["sec"]), cap_seconds_per_day)
        if key not in by_key_day:
            by_key_day[key] = {}
        by_key_day[key][d] = by_key_day[key].get(d, 0) + sec

    out: dict[tuple[str, int | None], dict] = {}
    for (user_email, project_id), day_secs in by_key_day.items():
        total_sec = sum(day_secs.values())
        hours = round(total_sec / 3600.0, 2)
        key = (user_email, project_id)
        out[key] = {
            DIM_LINES_ADDED: 0,
            "lines_removed": 0,
            DIM_COMMIT_COUNT: 0,
            DIM_FILES_CHANGED: 0,
            DIM_SESSION_DURATION_HOURS: hours,
            DIM_AGENT_REQUESTS: 0,
        }
    return out


async def _aggregate_usage(pool, period_type: str, period_key: str, caps: dict) -> dict[str, dict]:
    """Key email only (no project). Agent requests capped per day."""
    rng = period_key_to_date_range(period_type, period_key)
    if not rng:
        return {}
    start_d, end_d = rng
    cap_reqs = caps.get(CAP_AGENT_REQUESTS_PER_DAY)
    if cap_reqs is None:
        cap_reqs = 500

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT email, day, COALESCE(agent_requests, 0)::int AS agent_requests
            FROM daily_usage
            WHERE day >= $1 AND day <= $2
            """,
            start_d,
            end_d,
        )
    by_email_day: dict[str, dict[date, int]] = {}
    for r in rows:
        email = r["email"]
        d = r["day"]
        reqs = min(int(r["agent_requests"]), cap_reqs)
        if email not in by_email_day:
            by_email_day[email] = {}
        by_email_day[email][d] = by_email_day[email].get(d, 0) + reqs

    out: dict[str, dict] = {}
    for email, day_reqs in by_email_day.items():
        total_reqs = sum(day_reqs.values())
        out[email] = {
            DIM_AGENT_REQUESTS: total_reqs,
        }
    return out


def _merge_and_score(
    git_data: dict[tuple[str, int | None], dict],
    session_data: dict[tuple[str, int | None], dict],
    usage_data: dict[str, dict],
    weights: dict,
) -> dict[tuple[str, int | None], tuple[dict, dict, bool]]:
    """
    Merge three sources. Keys (user_email, project_id). project_id can be int or None for aggregate.
    Returns dict key -> (raw dict, score_breakdown dict, hook_adopted).
    """
    all_keys: set[tuple[str, int | None]] = set(git_data.keys()) | set(session_data.keys())
    # usage is per-email; we'll add it to every key with that email
    result: dict[tuple[str, int | None], tuple[dict, dict, bool]] = {}
    for key in all_keys:
        user_email, project_id = key
        raw = {
            DIM_LINES_ADDED: 0,
            "lines_removed": 0,
            DIM_COMMIT_COUNT: 0,
            DIM_FILES_CHANGED: 0,
            DIM_SESSION_DURATION_HOURS: 0.0,
            DIM_AGENT_REQUESTS: 0,
        }
        if key in git_data:
            g = git_data[key]
            raw[DIM_LINES_ADDED] = g.get(DIM_LINES_ADDED, 0)
            raw["lines_removed"] = g.get("lines_removed", 0)
            raw[DIM_COMMIT_COUNT] = g.get(DIM_COMMIT_COUNT, 0)
            raw[DIM_FILES_CHANGED] = g.get(DIM_FILES_CHANGED, 0)
        if key in session_data:
            s = session_data[key]
            raw[DIM_SESSION_DURATION_HOURS] = s.get(DIM_SESSION_DURATION_HOURS, 0)
        # agent_requests (daily_usage) is per-user only; add only in aggregate row, not per-project
        raw[DIM_AGENT_REQUESTS] = 0
        hook_adopted = key in session_data
        score_breakdown = {}
        for dim, w in weights.items():
            if isinstance(w, (int, float)):
                val = raw.get(dim, 0)
                if isinstance(val, (int, float)):
                    score_breakdown[dim] = float(Decimal(str(val)) * Decimal(str(w)))
                else:
                    score_breakdown[dim] = 0.0
        total = sum(score_breakdown.values())
        result[key] = (raw, score_breakdown, hook_adopted)
    return result


async def calculate_period(period_type: str, period_key: str, rule_id: int) -> None:
    """
    Load rule, aggregate git/sessions/usage, merge, upsert per-project rows,
    then upsert aggregate rows (user_email, project_id=NULL), then assign ranks (hook_adopted only), save snapshot.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rule = await conn.fetchrow(
            "SELECT id, weights, caps FROM incentive_rules WHERE id = $1 AND enabled = TRUE",
            rule_id,
        )
    if not rule:
        log.warning("No enabled rule id=%s", rule_id)
        return
    weights = _parse_jsonb(rule["weights"])
    caps = _parse_jsonb(rule["caps"])

    git_data = await _aggregate_git(pool, period_type, period_key)
    session_data = await _aggregate_sessions(pool, period_type, period_key, caps)
    usage_data = await _aggregate_usage(pool, period_type, period_key, caps)

    merged = _merge_and_score(git_data, session_data, usage_data, weights)
    if not merged:
        log.info("No data for period %s %s", period_type, period_key)
        return

    # Upsert per-project rows (project_id NOT NULL)
    for (user_email, project_id), (raw, score_breakdown, hook_adopted) in merged.items():
        if project_id is None:
            continue
        total = sum(score_breakdown.values())
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO contribution_scores (
                    user_email, project_id, period_type, period_key, rule_id,
                    lines_added, lines_removed, commit_count, files_changed,
                    session_duration_hours, agent_requests,
                    score_breakdown, total_score, rank, hook_adopted
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NULL, $14)
                ON CONFLICT (user_email, project_id, period_type, period_key) DO UPDATE SET
                    rule_id = EXCLUDED.rule_id,
                    lines_added = EXCLUDED.lines_added,
                    lines_removed = EXCLUDED.lines_removed,
                    commit_count = EXCLUDED.commit_count,
                    files_changed = EXCLUDED.files_changed,
                    session_duration_hours = EXCLUDED.session_duration_hours,
                    agent_requests = EXCLUDED.agent_requests,
                    score_breakdown = EXCLUDED.score_breakdown,
                    total_score = EXCLUDED.total_score,
                    rank = NULL,
                    hook_adopted = EXCLUDED.hook_adopted
                """,
                user_email,
                project_id,
                period_type,
                period_key,
                rule_id,
                raw.get(DIM_LINES_ADDED, 0),
                raw.get("lines_removed", 0),
                raw.get(DIM_COMMIT_COUNT, 0),
                raw.get(DIM_FILES_CHANGED, 0),
                raw.get(DIM_SESSION_DURATION_HOURS, 0),
                raw.get(DIM_AGENT_REQUESTS, 0),
                score_breakdown,
                total,
                hook_adopted,
            )

    # Aggregate (user_email, project_id=NULL): sum total_score per user, and hook_adopted = any project has session
    user_totals: dict[str, tuple[float, bool]] = {}
    for (user_email, project_id), (raw, score_breakdown, hook_adopted) in merged.items():
        total = sum(score_breakdown.values())
        if user_email not in user_totals:
            user_totals[user_email] = (0.0, False)
        prev_total, prev_hook = user_totals[user_email]
        user_totals[user_email] = (prev_total + total, prev_hook or hook_adopted)

    # Raw aggregate: sum raw dimensions across projects for (user_email, NULL); add usage once per user
    user_raw: dict[str, dict] = {}
    for (user_email, project_id), (raw, _, _) in merged.items():
        if user_email not in user_raw:
            user_raw[user_email] = {
                DIM_LINES_ADDED: 0, "lines_removed": 0, DIM_COMMIT_COUNT: 0,
                DIM_FILES_CHANGED: 0, DIM_SESSION_DURATION_HOURS: 0.0, DIM_AGENT_REQUESTS: 0,
            }
        for k, v in raw.items():
            if isinstance(v, (int, float)):
                user_raw[user_email][k] = user_raw[user_email].get(k, 0) + v
    for user_email, usage_row in usage_data.items():
        if user_email not in user_raw:
            user_raw[user_email] = {
                DIM_LINES_ADDED: 0, "lines_removed": 0, DIM_COMMIT_COUNT: 0,
                DIM_FILES_CHANGED: 0, DIM_SESSION_DURATION_HOURS: 0.0, DIM_AGENT_REQUESTS: 0,
            }
        user_raw[user_email][DIM_AGENT_REQUESTS] = usage_row.get(DIM_AGENT_REQUESTS, 0)
    user_breakdown: dict[str, dict] = {}
    for user_email, raw in user_raw.items():
        user_breakdown[user_email] = {}
        for dim, w in weights.items():
            if isinstance(w, (int, float)):
                val = raw.get(dim, 0)
                user_breakdown[user_email][dim] = float(Decimal(str(val)) * Decimal(str(w)))
    # Include users who only have usage (no git/session): they get aggregate row, rank NULL, hook_adopted=false
    for user_email in user_raw:
        if user_email not in user_totals:
            total_score = sum(user_breakdown.get(user_email, {}).values())
            user_totals[user_email] = (total_score, False)
    for user_email, (total_score, hook_adopted) in user_totals.items():
        raw = user_raw.get(user_email, {})
        score_breakdown = user_breakdown.get(user_email, {})
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO contribution_scores (
                    user_email, project_id, period_type, period_key, rule_id,
                    lines_added, lines_removed, commit_count, files_changed,
                    session_duration_hours, agent_requests,
                    score_breakdown, total_score, rank, hook_adopted
                ) VALUES ($1, NULL, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NULL, $13)
                ON CONFLICT (user_email, project_id, period_type, period_key) DO UPDATE SET
                    rule_id = EXCLUDED.rule_id,
                    lines_added = EXCLUDED.lines_added,
                    lines_removed = EXCLUDED.lines_removed,
                    commit_count = EXCLUDED.commit_count,
                    files_changed = EXCLUDED.files_changed,
                    session_duration_hours = EXCLUDED.session_duration_hours,
                    agent_requests = EXCLUDED.agent_requests,
                    score_breakdown = EXCLUDED.score_breakdown,
                    total_score = EXCLUDED.total_score,
                    rank = NULL,
                    hook_adopted = EXCLUDED.hook_adopted
                """,
                user_email,
                period_type,
                period_key,
                rule_id,
                raw.get(DIM_LINES_ADDED, 0),
                raw.get("lines_removed", 0),
                raw.get(DIM_COMMIT_COUNT, 0),
                raw.get(DIM_FILES_CHANGED, 0),
                raw.get(DIM_SESSION_DURATION_HOURS, 0),
                raw.get(DIM_AGENT_REQUESTS, 0),
                score_breakdown,
                total_score,
                hook_adopted,
            )

    # Rank: only hook_adopted=true, by total_score DESC on aggregate rows (project_id IS NULL)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT user_email, total_score
            FROM contribution_scores
            WHERE period_type = $1 AND period_key = $2 AND project_id IS NULL AND hook_adopted = TRUE
            ORDER BY total_score DESC
            """,
            period_type,
            period_key,
        )
    for rank, row in enumerate(rows, start=1):
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE contribution_scores
                SET rank = $1
                WHERE user_email = $2 AND project_id IS NULL AND period_type = $3 AND period_key = $4
                """,
                rank,
                row["user_email"],
                period_type,
                period_key,
            )

    # Snapshot
    snapshot_entries = [
        {
            "rank": rank,
            "user_email": r["user_email"],
            "total_score": float(r["total_score"]),
        }
        for rank, r in enumerate(rows, start=1)
    ]
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO leaderboard_snapshots (period_type, period_key, snapshot)
            VALUES ($1, $2, $3)
            ON CONFLICT (period_type, period_key) DO UPDATE SET snapshot = EXCLUDED.snapshot, created_at = NOW()
            """,
            period_type,
            period_key,
            {"entries": snapshot_entries, "generated_at": None},
        )
    log.info("Calculated %s %s: %d users, %d ranked", period_type, period_key, len(user_totals), len(rows))


async def run_calculate_latest(period_type: str, rule_id: int = 1) -> None:
    """Compute both the latest completed period and the current in-progress period."""
    from datetime import date
    today = date.today()
    keys: list[str] = []
    if period_type == "daily":
        yesterday = today - timedelta(days=1)
        keys = [yesterday.isoformat(), today.isoformat()]
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
