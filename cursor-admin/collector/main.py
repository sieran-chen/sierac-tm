"""
Cursor Admin 采集服务
- 接收 Hook 上报（/api/sessions）
- 提供管理端查询 API（/api/...）
- 定时同步 Cursor Admin API
"""

import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta

import asyncpg

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_code_sync import sync_ai_code_commits
from alerts import check_alerts
from config import settings
from contribution_engine import run_calculate_latest
from database import close_pool, get_pool, init_db
from git_collector import run_git_collect
from sync import run_full_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("main")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await run_full_sync()
    # Git collect runs in scheduler (_sync_and_alert) and via POST /api/admin/trigger-git-collect; not on startup to avoid long clone blocking serve

    scheduler.add_job(
        _sync_and_alert,
        "interval",
        minutes=settings.sync_interval_minutes,
        id="sync",
    )
    scheduler.add_job(
        _job_ai_code_sync,
        "interval",
        hours=1,
        id="ai_code_sync",
    )
    # Contribution score: daily 00:30, weekly Mon 01:00, monthly 1st 01:30 (Asia/Shanghai)
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Asia/Shanghai")
    except ImportError:
        tz = None
    scheduler.add_job(
        _job_contribution_daily,
        "cron",
        hour=0,
        minute=30,
        id="contribution_daily",
        timezone=tz,
    )
    scheduler.add_job(
        _job_contribution_weekly,
        "cron",
        day_of_week="mon",
        hour=1,
        minute=0,
        id="contribution_weekly",
        timezone=tz,
    )
    scheduler.add_job(
        _job_contribution_monthly,
        "cron",
        day=1,
        hour=1,
        minute=30,
        id="contribution_monthly",
        timezone=tz,
    )
    scheduler.start()
    log.info("Scheduler started, sync every %d min", settings.sync_interval_minutes)

    yield

    scheduler.shutdown()
    await close_pool()


async def _sync_and_alert():
    await run_full_sync()
    await check_alerts()
    try:
        await run_git_collect()
    except Exception as e:
        log.exception("Git collect failed: %s", e)
    try:
        await sync_ai_code_commits()
    except Exception as e:
        log.exception("AI code sync failed: %s", e)


async def _job_ai_code_sync():
    try:
        await sync_ai_code_commits()
    except Exception as e:
        log.exception("AI code sync job failed: %s", e)


async def _job_contribution_daily():
    try:
        await run_calculate_latest("daily")
    except Exception as e:
        log.exception("Contribution daily failed: %s", e)


async def _job_contribution_weekly():
    try:
        await run_calculate_latest("weekly")
    except Exception as e:
        log.exception("Contribution weekly failed: %s", e)


async def _job_contribution_monthly():
    try:
        await run_calculate_latest("monthly")
    except Exception as e:
        log.exception("Contribution monthly failed: %s", e)


app = FastAPI(title="Cursor Admin Collector", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 内部 API 鉴权 ────────────────────────────────────────────────────────────


def require_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ─── Hook 接收端点 ─────────────────────────────────────────────────────────────


class SessionPayload(BaseModel):
    event: str
    conversation_id: str
    user_email: str
    machine_id: str = ""
    workspace_roots: list[str] = []
    ended_at: int
    duration_seconds: int | None = None
    project_id: int | None = None


def _workspace_root_matches_rule(root: str, rule: str) -> bool:
    """Match root against rule (prefix). Normalize path separators and case for cross-platform.
    Strips trailing punctuation (e.g. full-width 。) from rule so UI typos do not break matching."""
    if not root or not rule:
        return False
    root_n = root.replace("\\", "/").strip().lower()
    rule_n = rule.replace("\\", "/").strip().lower()
    # Strip trailing punctuation/whitespace that may be entered in UI (e.g. "D:\AI\Sierac-tm。")
    rule_n = rule_n.rstrip("。，,; \t\n\r")
    if not rule_n:
        return False
    return root_n.startswith(rule_n)


async def _resolve_project_id_from_workspace_roots(pool, workspace_roots: list[str]) -> int | None:
    """Resolve project_id by matching workspace_roots against active projects' workspace_rules."""
    if not workspace_roots:
        return None
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, workspace_rules FROM projects WHERE status = 'active'"
        )
    for root in workspace_roots:
        for r in rows:
            rules = r["workspace_rules"] or []
            for rule in rules:
                if _workspace_root_matches_rule(root, rule):
                    return r["id"]
    return None


@app.post("/api/sessions", status_code=204)
async def receive_session(payload: SessionPayload):
    """Receive Hook session end event. Accept project_id; if missing, resolve from workspace_rules."""
    from datetime import datetime, timezone

    pool = await get_pool()
    ended_dt = datetime.fromtimestamp(payload.ended_at, tz=timezone.utc)
    started_dt = None
    if payload.duration_seconds is not None:
        started_dt = datetime.fromtimestamp(
            payload.ended_at - payload.duration_seconds, tz=timezone.utc
        )

    project_id = payload.project_id
    if project_id is None and payload.workspace_roots:
        project_id = await _resolve_project_id_from_workspace_roots(pool, payload.workspace_roots)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO agent_sessions
                (conversation_id, user_email, machine_id, workspace_roots, started_at, ended_at, duration_seconds, project_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            ON CONFLICT (conversation_id) DO NOTHING
            """,
            payload.conversation_id,
            payload.user_email,
            payload.machine_id,
            payload.workspace_roots,
            started_dt,
            ended_dt,
            payload.duration_seconds,
            project_id,
        )


# ─── 查询 API（管理端使用） ────────────────────────────────────────────────────


@app.get("/api/members", dependencies=[Depends(require_api_key)])
async def list_members():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM members WHERE is_removed=FALSE ORDER BY email")
    return [dict(r) for r in rows]


@app.get("/api/usage/daily", dependencies=[Depends(require_api_key)])
async def daily_usage(
    email: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    """按用户/日期范围查询每日用量"""
    pool = await get_pool()
    start_date = date.fromisoformat(start) if start else date.today() - timedelta(days=30)
    end_date = date.fromisoformat(end) if end else date.today()

    async with pool.acquire() as conn:
        if email:
            rows = await conn.fetch(
                "SELECT * FROM daily_usage WHERE email=$1 AND day BETWEEN $2 AND $3 ORDER BY day DESC",
                email,
                start_date,
                end_date,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM daily_usage WHERE day BETWEEN $1 AND $2 ORDER BY email, day DESC",
                start_date,
                end_date,
            )
    return [dict(r) for r in rows]


@app.get("/api/usage/spend", dependencies=[Depends(require_api_key)])
async def spend_data():
    """当前计费周期各成员支出"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.*, m.name FROM spend_snapshots s
            LEFT JOIN members m ON m.email = s.email
            WHERE s.billing_cycle_start = (SELECT MAX(billing_cycle_start) FROM spend_snapshots)
            ORDER BY s.spend_cents DESC
            """
        )
    return [dict(r) for r in rows]


@app.get("/api/sessions", dependencies=[Depends(require_api_key)])
async def list_sessions(
    email: str | None = Query(None),
    workspace: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    """按用户/工作目录/时间范围查询 Agent 会话"""
    pool = await get_pool()
    start_date = date.fromisoformat(start) if start else date.today() - timedelta(days=30)
    end_date = date.fromisoformat(end) if end else date.today()
    offset = (page - 1) * page_size

    conditions = ["ended_at::date BETWEEN $1 AND $2"]
    params: list = [start_date, end_date]
    idx = 3

    if email:
        conditions.append(f"user_email = ${idx}")
        params.append(email)
        idx += 1
    if workspace:
        conditions.append(f"primary_workspace ILIKE ${idx}")
        params.append(f"%{workspace}%")
        idx += 1

    where = " AND ".join(conditions)
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM agent_sessions WHERE {where}", *params)
        rows = await conn.fetch(
            f"SELECT * FROM agent_sessions WHERE {where} ORDER BY ended_at DESC LIMIT {page_size} OFFSET {offset}",
            *params,
        )
    return {"total": total, "page": page, "page_size": page_size, "data": [dict(r) for r in rows]}


@app.get("/api/sessions/summary", dependencies=[Depends(require_api_key)])
async def sessions_summary(
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    """按用户 + 工作目录汇总：会话数、总时长"""
    pool = await get_pool()
    start_date = date.fromisoformat(start) if start else date.today() - timedelta(days=30)
    end_date = date.fromisoformat(end) if end else date.today()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                user_email,
                primary_workspace,
                COUNT(*)                                AS session_count,
                COALESCE(SUM(duration_seconds), 0)     AS total_seconds,
                MIN(ended_at)                           AS first_seen,
                MAX(ended_at)                           AS last_seen
            FROM agent_sessions
            WHERE ended_at::date BETWEEN $1 AND $2
              AND primary_workspace IS NOT NULL
            GROUP BY user_email, primary_workspace
            ORDER BY user_email, total_seconds DESC
            """,
            start_date,
            end_date,
        )
    return [dict(r) for r in rows]


@app.get("/api/sessions/summary-by-project", dependencies=[Depends(require_api_key)])
async def sessions_summary_by_project(
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    """按用户 + 项目聚合：会话数、总时长；project_id 为空时显示为「未归属」。"""
    pool = await get_pool()
    start_date = date.fromisoformat(start) if start else date.today() - timedelta(days=30)
    end_date = date.fromisoformat(end) if end else date.today()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                a.project_id,
                COALESCE(p.name, '未归属') AS project_name,
                a.user_email,
                COUNT(*) AS session_count,
                COALESCE(SUM(a.duration_seconds), 0)::bigint AS total_seconds,
                MIN(a.ended_at) AS first_seen,
                MAX(a.ended_at) AS last_seen
            FROM agent_sessions a
            LEFT JOIN projects p ON p.id = a.project_id
            WHERE a.ended_at::date BETWEEN $1 AND $2
            GROUP BY a.project_id, p.name, a.user_email
            ORDER BY project_name, a.user_email, total_seconds DESC
            """,
            start_date,
            end_date,
        )
    return [
        {
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "user_email": r["user_email"],
            "session_count": r["session_count"],
            "total_seconds": r["total_seconds"],
            "first_seen": r["first_seen"].isoformat() if r["first_seen"] and hasattr(r["first_seen"], "isoformat") else (str(r["first_seen"]) if r["first_seen"] else None),
            "last_seen": r["last_seen"].isoformat() if r["last_seen"] and hasattr(r["last_seen"], "isoformat") else (str(r["last_seen"]) if r["last_seen"] else None),
        }
        for r in rows
    ]


# ─── 告警规则 CRUD ─────────────────────────────────────────────────────────────


class AlertRuleIn(BaseModel):
    name: str
    metric: str
    scope: str
    target_email: str | None = None
    threshold: float
    notify_channels: list[dict] = []
    enabled: bool = True


@app.get("/api/alerts/rules", dependencies=[Depends(require_api_key)])
async def list_alert_rules():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM alert_rules ORDER BY id")
    return [dict(r) for r in rows]


@app.post("/api/alerts/rules", dependencies=[Depends(require_api_key)])
async def create_alert_rule(body: AlertRuleIn):
    import json

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO alert_rules (name, metric, scope, target_email, threshold, notify_channels, enabled)
            VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING *
            """,
            body.name,
            body.metric,
            body.scope,
            body.target_email,
            body.threshold,
            json.dumps(body.notify_channels),
            body.enabled,
        )
    return dict(row)


@app.put("/api/alerts/rules/{rule_id}", dependencies=[Depends(require_api_key)])
async def update_alert_rule(rule_id: int, body: AlertRuleIn):
    import json

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE alert_rules SET name=$1,metric=$2,scope=$3,target_email=$4,
                threshold=$5,notify_channels=$6,enabled=$7
            WHERE id=$8 RETURNING *
            """,
            body.name,
            body.metric,
            body.scope,
            body.target_email,
            body.threshold,
            json.dumps(body.notify_channels),
            body.enabled,
            rule_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found")
    return dict(row)


@app.delete("/api/alerts/rules/{rule_id}", dependencies=[Depends(require_api_key)], status_code=204)
async def delete_alert_rule(rule_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM alert_rules WHERE id=$1", rule_id)


@app.get("/api/alerts/events", dependencies=[Depends(require_api_key)])
async def list_alert_events(limit: int = Query(50, ge=1, le=500)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT e.*, r.name AS rule_name, r.metric
            FROM alert_events e
            JOIN alert_rules r ON r.id = e.rule_id
            ORDER BY e.triggered_at DESC LIMIT $1
            """,
            limit,
        )
    return [dict(r) for r in rows]


# ─── 项目 CRUD（管理端） ───────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    git_repos: list[str] = []
    member_emails: list[str] = []
    created_by: str
    budget_amount: float | None = None
    budget_period: str = "monthly"
    incentive_pool: float | None = None
    incentive_rule_id: int | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    git_repos: list[str] | None = None
    member_emails: list[str] | None = None
    status: str | None = None
    budget_amount: float | None = None
    budget_period: str | None = None
    incentive_pool: float | None = None
    incentive_rule_id: int | None = None


@app.get("/api/projects", dependencies=[Depends(require_api_key)])
async def list_projects(status: str | None = Query(None)):
    """List projects; optional ?status=active to filter."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM projects WHERE status=$1 ORDER BY id",
                status,
            )
        else:
            rows = await conn.fetch("SELECT * FROM projects ORDER BY id")
    return [dict(r) for r in rows]


@app.post("/api/projects", dependencies=[Depends(require_api_key)])
async def create_project(body: ProjectCreate):
    """Create project (v3.0 lightweight: register info + git_repos, no repo creation or Hook injection)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO projects (name, description, git_repos, member_emails, created_by,
                                  budget_amount, budget_period, incentive_pool, incentive_rule_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *
            """,
            body.name,
            body.description,
            body.git_repos,
            body.member_emails,
            body.created_by,
            body.budget_amount,
            body.budget_period,
            body.incentive_pool,
            body.incentive_rule_id,
        )
    return dict(row)



@app.get("/api/projects/{project_id}", dependencies=[Depends(require_api_key)])
async def get_project(project_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM projects WHERE id=$1", project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@app.get("/api/projects/{project_id}/contributions", dependencies=[Depends(require_api_key)])
async def get_project_contributions(
    project_id: int,
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    """Git contributions for this project (by author, by date). Optional start/end date filter."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM projects WHERE id=$1", project_id)
    if not exists:
        raise HTTPException(status_code=404, detail="Project not found")
    conditions = ["project_id=$1"]
    params: list = [project_id]
    idx = 2
    if start:
        conditions.append(f"commit_date >= ${idx}")
        params.append(date.fromisoformat(start))
        idx += 1
    if end:
        conditions.append(f"commit_date <= ${idx}")
        params.append(date.fromisoformat(end))
        idx += 1
    where = " AND ".join(conditions)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT author_email, commit_date, commit_count, lines_added, lines_removed, files_changed
            FROM git_contributions WHERE {where}
            ORDER BY commit_date DESC, author_email
            """,
            *params,
        )
    return [
        {
            "author_email": r["author_email"],
            "commit_date": r["commit_date"].isoformat() if hasattr(r["commit_date"], "isoformat") else str(r["commit_date"]),
            "commit_count": r["commit_count"],
            "lines_added": r["lines_added"],
            "lines_removed": r["lines_removed"],
            "files_changed": r["files_changed"],
        }
        for r in rows
    ]


@app.get("/api/projects/{project_id}/summary", dependencies=[Depends(require_api_key)])
async def get_project_summary(project_id: int):
    """Project summary: budget, AI code contribution (from ai_code_commits), member breakdown."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        proj = await conn.fetchrow("SELECT * FROM projects WHERE id=$1", project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    async with pool.acquire() as conn:
        # AI code contribution totals
        contrib = await conn.fetchrow(
            """
            SELECT
                COALESCE(SUM(tab_lines_added + composer_lines_added), 0)::int AS total_ai_lines,
                COALESCE(SUM(total_lines_added), 0)::int AS total_lines,
                COUNT(DISTINCT commit_hash)::int AS commit_count,
                COUNT(DISTINCT user_email)::int AS member_count
            FROM ai_code_commits WHERE project_id = $1
            """,
            project_id,
        )
        # Per-member breakdown
        members = await conn.fetch(
            """
            SELECT user_email,
                   SUM(tab_lines_added + composer_lines_added)::int AS ai_lines_added,
                   SUM(total_lines_added)::int AS total_lines_added,
                   COUNT(DISTINCT commit_hash)::int AS commit_count
            FROM ai_code_commits WHERE project_id = $1
            GROUP BY user_email ORDER BY ai_lines_added DESC
            """,
            project_id,
        )
        # Budget spend estimate from spend_snapshots (sum for member_emails)
        member_emails = list(proj["member_emails"] or [])
        spend_row = await conn.fetchrow(
            """
            SELECT COALESCE(SUM(spend_cents), 0)::bigint AS total_spend_cents
            FROM spend_snapshots
            WHERE billing_cycle_start = (SELECT MAX(billing_cycle_start) FROM spend_snapshots)
              AND email = ANY($1)
            """,
            member_emails,
        ) if member_emails else None

    total_ai = contrib["total_ai_lines"] or 0
    total_lines = contrib["total_lines"] or 0
    spent_cents = spend_row["total_spend_cents"] if spend_row else 0

    member_list = []
    for r in members:
        ai = r["ai_lines_added"] or 0
        tl = r["total_lines_added"] or 0
        member_list.append({
            "user_email": r["user_email"],
            "ai_lines_added": ai,
            "total_lines_added": tl,
            "ai_ratio": round(ai / tl, 4) if tl else 0,
            "commit_count": r["commit_count"],
            "contribution_pct": round(ai / total_ai, 4) if total_ai else 0,
        })

    return {
        "project": dict(proj),
        "budget": {
            "amount": float(proj["budget_amount"]) if proj["budget_amount"] else None,
            "period": proj["budget_period"],
            "spent_estimate": round(spent_cents / 100, 2),
        },
        "contribution": {
            "total_ai_lines": total_ai,
            "total_lines": total_lines,
            "ai_ratio": round(total_ai / total_lines, 4) if total_lines else 0,
            "commit_count": contrib["commit_count"] or 0,
            "member_count": contrib["member_count"] or 0,
        },
        "incentive_pool": float(proj["incentive_pool"]) if proj["incentive_pool"] else None,
        "members": member_list,
    }


@app.put("/api/projects/{project_id}", dependencies=[Depends(require_api_key)])
async def update_project(project_id: int, body: ProjectUpdate):
    pool = await get_pool()
    updates: list[str] = []
    params: list = []
    idx = 1
    for field, col in [
        ("name", "name"), ("description", "description"), ("git_repos", "git_repos"),
        ("member_emails", "member_emails"), ("status", "status"),
        ("budget_amount", "budget_amount"), ("budget_period", "budget_period"),
        ("incentive_pool", "incentive_pool"), ("incentive_rule_id", "incentive_rule_id"),
    ]:
        val = getattr(body, field)
        if val is not None:
            updates.append(f"{col}=${idx}")
            params.append(val)
            idx += 1
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates.append("updated_at=NOW()")
    params.append(project_id)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE projects SET {', '.join(updates)} WHERE id=${idx} RETURNING *",
            *params,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@app.delete("/api/projects/{project_id}", dependencies=[Depends(require_api_key)], status_code=204)
async def archive_project(project_id: int):
    """Soft delete: set status to archived."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE projects SET status='archived', updated_at=NOW() WHERE id=$1",
            project_id,
        )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Project not found")




# ─── 成员端：我的贡献 ──────────────────────────────────────────────────────────


@app.get("/api/contributions/my", dependencies=[Depends(require_api_key)])
async def get_my_contributions(
    email: str = Query(..., description="Current user email"),
    start: str | None = Query(None),
    end: str | None = Query(None),
    period_type: str | None = Query(None, description="weekly | monthly; with period_key returns score view"),
    period_key: str | None = Query(None, description="e.g. 2026-W08 or 2026-02"),
):
    """
    Member-facing contributions. With period_type+period_key: score, rank, breakdown, projects.
    Without: raw git contributions list (optional start/end).
    """
    if period_type and period_key:
        pool = await get_pool()
        try:
            async with pool.acquire() as conn:
                agg = await conn.fetchrow(
                    """
                    SELECT rank, ai_lines_added, total_lines_added, ai_ratio, commit_count, incentive_amount
                    FROM contribution_scores
                    WHERE user_email=$1 AND project_id IS NULL AND period_type=$2 AND period_key=$3
                    """,
                    email, period_type, period_key,
                )
                proj_rows = await conn.fetch(
                    """
                    SELECT c.project_id, p.name AS project_name,
                           c.ai_lines_added, c.total_lines_added, c.ai_ratio,
                           c.contribution_pct, c.incentive_amount
                    FROM contribution_scores c
                    JOIN projects p ON p.id = c.project_id
                    WHERE c.user_email=$1 AND c.period_type=$2 AND c.period_key=$3 AND c.project_id IS NOT NULL
                    ORDER BY c.ai_lines_added DESC
                    """,
                    email, period_type, period_key,
                )
        except asyncpg.UndefinedTableError:
            return {"user_email": email, "period_type": period_type, "period_key": period_key,
                    "rank": None, "ai_lines_added": 0, "total_lines_added": 0, "ai_ratio": 0,
                    "commit_count": 0, "incentive_amount": 0, "projects": []}
        if not agg:
            return {"user_email": email, "period_type": period_type, "period_key": period_key,
                    "rank": None, "ai_lines_added": 0, "total_lines_added": 0, "ai_ratio": 0,
                    "commit_count": 0, "incentive_amount": 0, "projects": []}
        return {
            "user_email": email,
            "period_type": period_type,
            "period_key": period_key,
            "rank": agg["rank"],
            "ai_lines_added": agg["ai_lines_added"],
            "total_lines_added": agg["total_lines_added"],
            "ai_ratio": float(agg["ai_ratio"]),
            "commit_count": agg["commit_count"],
            "incentive_amount": float(agg["incentive_amount"]),
            "projects": [
                {
                    "project_id": r["project_id"],
                    "project_name": r["project_name"],
                    "ai_lines_added": r["ai_lines_added"],
                    "total_lines_added": r["total_lines_added"],
                    "ai_ratio": float(r["ai_ratio"]),
                    "contribution_pct": float(r["contribution_pct"]),
                    "incentive_amount": float(r["incentive_amount"]),
                }
                for r in proj_rows
            ],
        }

    pool = await get_pool()
    conditions = ["g.author_email = $1", "p.status = 'active'"]
    params: list = [email]
    idx = 2
    if start:
        conditions.append(f"g.commit_date >= ${idx}")
        params.append(date.fromisoformat(start))
        idx += 1
    if end:
        conditions.append(f"g.commit_date <= ${idx}")
        params.append(date.fromisoformat(end))
        idx += 1
    where = " AND ".join(conditions)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT g.project_id, p.name AS project_name, g.commit_date, g.commit_count,
                   g.lines_added, g.lines_removed, g.files_changed
            FROM git_contributions g
            JOIN projects p ON p.id = g.project_id
            WHERE {where}
            ORDER BY g.commit_date DESC, g.project_id
            """,
            *params,
        )
    return [
        {
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "commit_date": r["commit_date"].isoformat() if hasattr(r["commit_date"], "isoformat") else str(r["commit_date"]),
            "commit_count": r["commit_count"],
            "lines_added": r["lines_added"],
            "lines_removed": r["lines_removed"],
            "files_changed": r["files_changed"],
        }
        for r in rows
    ]


# ─── 排行榜 ────────────────────────────────────────────────────────────────────


@app.get("/api/contributions/leaderboard", dependencies=[Depends(require_api_key)])
async def get_leaderboard(
    period_type: str = Query(..., description="weekly | monthly"),
    period_key: str = Query(..., description="e.g. 2026-W08 or 2026-02"),
):
    """Leaderboard for the given period. Ranked by ai_lines_added DESC (all members, no Hook filter)."""
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT user_email, rank, ai_lines_added, total_lines_added, ai_ratio,
                       commit_count, incentive_amount
                FROM contribution_scores
                WHERE period_type = $1 AND period_key = $2 AND project_id IS NULL
                ORDER BY rank ASC NULLS LAST, ai_lines_added DESC
                """,
                period_type,
                period_key,
            )
            snapshot = await conn.fetchrow(
                "SELECT created_at FROM leaderboard_snapshots WHERE period_type=$1 AND period_key=$2",
                period_type, period_key,
            )
    except asyncpg.UndefinedTableError:
        return {"period_type": period_type, "period_key": period_key, "generated_at": None, "entries": []}
    generated_at = snapshot["created_at"].isoformat() if snapshot and snapshot.get("created_at") else None
    return {
        "period_type": period_type,
        "period_key": period_key,
        "generated_at": generated_at,
        "entries": [
            {
                "rank": r["rank"],
                "user_email": r["user_email"],
                "ai_lines_added": r["ai_lines_added"],
                "total_lines_added": r["total_lines_added"],
                "ai_ratio": float(r["ai_ratio"]),
                "commit_count": r["commit_count"],
                "incentive_amount": float(r["incentive_amount"]),
            }
            for r in rows
        ],
    }


# ─── 激励规则 CRUD ─────────────────────────────────────────────────────────────


class IncentiveRuleCreate(BaseModel):
    name: str
    period_type: str = "weekly"
    weights: dict
    caps: dict = {}
    enabled: bool = True


class IncentiveRuleUpdate(BaseModel):
    name: str | None = None
    period_type: str | None = None
    weights: dict | None = None
    caps: dict | None = None
    enabled: bool | None = None


def _norm_jsonb(val):
    """Normalize JSONB/dict for JSON response (asyncpg may return dict, str, or custom type)."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        import json as _json
        try:
            parsed = _json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    try:
        return dict(val)
    except (TypeError, ValueError):
        return {}


@app.get("/api/incentive-rules", dependencies=[Depends(require_api_key)])
async def list_incentive_rules(enabled_only: bool = Query(False)):
    """List incentive rules. enabled_only=true returns only enabled rules."""
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            if enabled_only:
                rows = await conn.fetch(
                    "SELECT id, name, period_type, weights, caps, enabled, created_at, updated_at FROM incentive_rules WHERE enabled = TRUE ORDER BY id"
                )
            else:
                rows = await conn.fetch(
                    "SELECT id, name, period_type, weights, caps, enabled, created_at, updated_at FROM incentive_rules ORDER BY id"
                )
    except asyncpg.UndefinedTableError:
        return []
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "period_type": r["period_type"],
            "weights": _norm_jsonb(r.get("weights")),
            "caps": _norm_jsonb(r.get("caps")),
            "enabled": r["enabled"],
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
        }
        for r in rows
    ]


@app.post("/api/incentive-rules", dependencies=[Depends(require_api_key)], status_code=201)
async def create_incentive_rule(body: IncentiveRuleCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO incentive_rules (name, period_type, weights, caps, enabled)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, name, period_type, weights, caps, enabled, created_at, updated_at
            """,
            body.name,
            body.period_type,
            body.weights,
            body.caps,
            body.enabled,
        )
    return {
        "id": row["id"],
        "name": row["name"],
        "period_type": row["period_type"],
        "weights": dict(row["weights"] or {}),
        "caps": dict(row["caps"] or {}),
        "enabled": row["enabled"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


@app.get("/api/incentive-rules/{rule_id}", dependencies=[Depends(require_api_key)])
async def get_incentive_rule(rule_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, period_type, weights, caps, enabled, created_at, updated_at FROM incentive_rules WHERE id = $1",
            rule_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Incentive rule not found")
    return {
        "id": row["id"],
        "name": row["name"],
        "period_type": row["period_type"],
        "weights": dict(row["weights"] or {}),
        "caps": dict(row["caps"] or {}),
        "enabled": row["enabled"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


@app.put("/api/incentive-rules/{rule_id}", dependencies=[Depends(require_api_key)])
async def update_incentive_rule(rule_id: int, body: IncentiveRuleUpdate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, name, period_type, weights, caps, enabled FROM incentive_rules WHERE id = $1", rule_id)
        if not row:
            raise HTTPException(status_code=404, detail="Incentive rule not found")
        updates = []
        params = []
        idx = 1
        if body.name is not None:
            updates.append(f"name = ${idx}")
            params.append(body.name)
            idx += 1
        if body.period_type is not None:
            updates.append(f"period_type = ${idx}")
            params.append(body.period_type)
            idx += 1
        if body.weights is not None:
            updates.append(f"weights = ${idx}")
            params.append(body.weights)
            idx += 1
        if body.caps is not None:
            updates.append(f"caps = ${idx}")
            params.append(body.caps)
            idx += 1
        if body.enabled is not None:
            updates.append(f"enabled = ${idx}")
            params.append(body.enabled)
            idx += 1
        if not updates:
            return {
                "id": row["id"],
                "name": row["name"],
                "period_type": row["period_type"],
                "weights": dict(row["weights"] or {}),
                "caps": dict(row["caps"] or {}),
                "enabled": row["enabled"],
            }
        updates.append("updated_at = NOW()")
        params.extend([rule_id])
        await conn.execute(
            f"UPDATE incentive_rules SET {', '.join(updates)} WHERE id = ${idx}",
            *params,
        )
        row = await conn.fetchrow(
            "SELECT id, name, period_type, weights, caps, enabled, created_at, updated_at FROM incentive_rules WHERE id = $1",
            rule_id,
        )
    return {
        "id": row["id"],
        "name": row["name"],
        "period_type": row["period_type"],
        "weights": dict(row["weights"] or {}),
        "caps": dict(row["caps"] or {}),
        "enabled": row["enabled"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


@app.delete("/api/incentive-rules/{rule_id}", dependencies=[Depends(require_api_key)], status_code=204)
async def delete_incentive_rule(rule_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id FROM incentive_rules WHERE id = $1", rule_id)
        if not row:
            raise HTTPException(status_code=404, detail="Incentive rule not found")
        await conn.execute("UPDATE incentive_rules SET enabled = FALSE WHERE id = $1", rule_id)


@app.post("/api/incentive-rules/{rule_id}/recalculate", dependencies=[Depends(require_api_key)])
async def recalculate_incentive_rule(rule_id: int):
    """Trigger contribution calculation for the rule's period_type (latest period)."""
    from contribution_engine import run_calculate_latest

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, period_type FROM incentive_rules WHERE id = $1 AND enabled = TRUE",
            rule_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Incentive rule not found or disabled")
    await run_calculate_latest(row["period_type"], rule_id=rule_id)
    return {"ok": True, "message": f"Recalculated {row['period_type']} for rule {rule_id}."}


# ─── AI Code Commits 查询 API ─────────────────────────────────────────────────


def _ts(v) -> str | None:
    return v.isoformat() if v and hasattr(v, "isoformat") else (str(v) if v else None)


@app.get("/api/ai-commits", dependencies=[Depends(require_api_key)])
async def list_ai_commits(
    project_id: int | None = Query(None),
    user_email: str | None = Query(None),
    start: str | None = Query(None),
    end: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    """
    List ai_code_commits with optional filters.
    Returns items with ai_lines_added (tab+composer), total_lines_added, ai_ratio, project_name.
    """
    pool = await get_pool()
    conditions: list[str] = []
    params: list = []
    idx = 1

    if project_id is not None:
        conditions.append(f"c.project_id = ${idx}")
        params.append(project_id)
        idx += 1
    if user_email:
        conditions.append(f"c.user_email = ${idx}")
        params.append(user_email)
        idx += 1
    if start:
        conditions.append(f"c.commit_ts >= ${idx}")
        params.append(date.fromisoformat(start))
        idx += 1
    if end:
        conditions.append(f"c.commit_ts < (${idx}::date + INTERVAL '1 day')")
        params.append(date.fromisoformat(end))
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * page_size

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM ai_code_commits c {where}", *params
        )
        rows = await conn.fetch(
            f"""
            SELECT c.commit_hash, c.user_email, c.repo_name, c.branch_name,
                   c.tab_lines_added + c.composer_lines_added AS ai_lines_added,
                   c.total_lines_added, c.commit_message, c.commit_ts,
                   c.project_id, p.name AS project_name
            FROM ai_code_commits c
            LEFT JOIN projects p ON p.id = c.project_id
            {where}
            ORDER BY c.commit_ts DESC
            LIMIT {page_size} OFFSET {offset}
            """,
            *params,
        )

    items = []
    for r in rows:
        ai = r["ai_lines_added"] or 0
        total_l = r["total_lines_added"] or 0
        items.append({
            "commit_hash": r["commit_hash"],
            "user_email": r["user_email"],
            "repo_name": r["repo_name"],
            "branch_name": r["branch_name"],
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "ai_lines_added": ai,
            "total_lines_added": total_l,
            "ai_ratio": round(ai / total_l, 4) if total_l else 0,
            "commit_message": r["commit_message"],
            "commit_ts": _ts(r["commit_ts"]),
        })
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@app.get("/api/ai-commits/summary", dependencies=[Depends(require_api_key)])
async def ai_commits_summary(
    project_id: int | None = Query(None),
    period: str | None = Query(None, description="monthly | weekly"),
    period_key: str | None = Query(None, description="e.g. 2026-02 or 2026-W08"),
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    """
    Aggregate ai_code_commits by project+member.
    Supports period filter (monthly/weekly) or explicit start/end.
    """
    pool = await get_pool()

    # Resolve date range from period or explicit start/end
    start_dt: date | None = None
    end_dt: date | None = None
    if period and period_key:
        range_result = None
        from contribution_engine import period_key_to_date_range
        range_result = period_key_to_date_range(period, period_key)
        if range_result:
            start_dt, end_dt = range_result
    if start:
        start_dt = date.fromisoformat(start)
    if end:
        end_dt = date.fromisoformat(end)

    conditions: list[str] = []
    params: list = []
    idx = 1
    if project_id is not None:
        conditions.append(f"c.project_id = ${idx}")
        params.append(project_id)
        idx += 1
    if start_dt:
        conditions.append(f"c.commit_ts >= ${idx}")
        params.append(start_dt)
        idx += 1
    if end_dt:
        conditions.append(f"c.commit_ts < (${idx}::date + INTERVAL '1 day')")
        params.append(end_dt)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT c.project_id, p.name AS project_name, c.user_email,
                   SUM(c.tab_lines_added + c.composer_lines_added)::int AS ai_lines_added,
                   SUM(c.total_lines_added)::int AS total_lines_added,
                   COUNT(DISTINCT c.commit_hash)::int AS commit_count
            FROM ai_code_commits c
            LEFT JOIN projects p ON p.id = c.project_id
            {where}
            GROUP BY c.project_id, p.name, c.user_email
            ORDER BY ai_lines_added DESC
            """,
            *params,
        )

    # Group by project
    projects_map: dict = {}
    for r in rows:
        pid = r["project_id"]
        if pid not in projects_map:
            projects_map[pid] = {
                "project_id": pid,
                "project_name": r["project_name"],
                "members": [],
                "totals": {"ai_lines_added": 0, "total_lines_added": 0, "commit_count": 0},
            }
        ai = r["ai_lines_added"] or 0
        total_l = r["total_lines_added"] or 0
        projects_map[pid]["members"].append({
            "user_email": r["user_email"],
            "ai_lines_added": ai,
            "total_lines_added": total_l,
            "ai_ratio": round(ai / total_l, 4) if total_l else 0,
            "commit_count": r["commit_count"],
        })
        projects_map[pid]["totals"]["ai_lines_added"] += ai
        projects_map[pid]["totals"]["total_lines_added"] += total_l
        projects_map[pid]["totals"]["commit_count"] += r["commit_count"]

    for p in projects_map.values():
        t = p["totals"]
        t["ai_ratio"] = round(t["ai_lines_added"] / t["total_lines_added"], 4) if t["total_lines_added"] else 0

    return {
        "period": period_key,
        "projects": list(projects_map.values()),
    }


@app.get("/api/ai-commits/my", dependencies=[Depends(require_api_key)])
async def my_ai_commits(
    email: str = Query(..., description="Member email"),
    period: str | None = Query(None, description="monthly | weekly"),
    period_key: str | None = Query(None, description="e.g. 2026-02 or 2026-W08"),
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    """Member-facing: my AI code contribution summary with per-project breakdown and trend."""
    pool = await get_pool()

    start_dt: date | None = None
    end_dt: date | None = None
    if period and period_key:
        from contribution_engine import period_key_to_date_range
        result = period_key_to_date_range(period, period_key)
        if result:
            start_dt, end_dt = result
    if start:
        start_dt = date.fromisoformat(start)
    if end:
        end_dt = date.fromisoformat(end)

    conditions = ["c.user_email = $1"]
    params: list = [email]
    idx = 2
    if start_dt:
        conditions.append(f"c.commit_ts >= ${idx}")
        params.append(start_dt)
        idx += 1
    if end_dt:
        conditions.append(f"c.commit_ts < (${idx}::date + INTERVAL '1 day')")
        params.append(end_dt)
        idx += 1

    where = "WHERE " + " AND ".join(conditions)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT c.project_id, p.name AS project_name,
                   SUM(c.tab_lines_added + c.composer_lines_added)::int AS ai_lines_added,
                   SUM(c.total_lines_added)::int AS total_lines_added,
                   COUNT(DISTINCT c.commit_hash)::int AS commit_count
            FROM ai_code_commits c
            LEFT JOIN projects p ON p.id = c.project_id
            {where}
            GROUP BY c.project_id, p.name
            ORDER BY ai_lines_added DESC
            """,
            *params,
        )

    total_ai = sum(r["ai_lines_added"] or 0 for r in rows)
    total_lines = sum(r["total_lines_added"] or 0 for r in rows)
    projects = [
        {
            "project_id": r["project_id"],
            "project_name": r["project_name"],
            "ai_lines_added": r["ai_lines_added"] or 0,
            "total_lines_added": r["total_lines_added"] or 0,
            "ai_ratio": round((r["ai_lines_added"] or 0) / r["total_lines_added"], 4) if r["total_lines_added"] else 0,
            "commit_count": r["commit_count"],
        }
        for r in rows
    ]

    return {
        "user_email": email,
        "period": period_key,
        "total_ai_lines": total_ai,
        "total_lines": total_lines,
        "ai_ratio": round(total_ai / total_lines, 4) if total_lines else 0,
        "projects": projects,
    }


# ─── 健康检查与闭环健康 ───────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/admin/trigger-git-collect", status_code=200, dependencies=[Depends(require_api_key)])
async def trigger_git_collect():
    """Manually trigger Git collection for all active projects with git_repos."""
    try:
        await run_git_collect()
        return {"ok": True, "message": "Git collect completed"}
    except Exception as e:
        log.exception("Git collect failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health/loop", dependencies=[Depends(require_api_key)])
async def health_loop(days: int = Query(7, ge=1, le=30)):
    """
    Loop health: whether we have received any Hook sessions in the last N days.
    Used by admin UI to show "loop not connected" guidance when loop_ok is false.
    """
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*)::int AS sessions_count,
                    MAX(ended_at) AS last_session_at,
                    COUNT(DISTINCT user_email)::int AS members_count
                FROM agent_sessions
                WHERE ended_at >= NOW() - ($1::text || ' days')::interval
                """,
                str(days),
            )
    except asyncpg.UndefinedTableError:
        return {
            "loop_ok": False,
            "days_checked": days,
            "last_session_at": None,
            "sessions_count_7d": 0,
            "members_with_sessions_7d": 0,
        }
    if not row or row["sessions_count"] == 0:
        return {
            "loop_ok": False,
            "days_checked": days,
            "last_session_at": None,
            "sessions_count_7d": 0,
            "members_with_sessions_7d": 0,
        }
    return {
        "loop_ok": True,
        "days_checked": days,
        "last_session_at": row["last_session_at"].isoformat() if row.get("last_session_at") else None,
        "sessions_count_7d": row["sessions_count"],
        "members_with_sessions_7d": row["members_count"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=False)
