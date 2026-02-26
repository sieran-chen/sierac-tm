"""
Cursor Admin 采集服务
- 接收 Hook 上报（/api/sessions）
- 提供管理端查询 API（/api/...）
- 定时同步 Cursor Admin API
"""

import logging
from contextlib import asynccontextmanager
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

    scheduler.add_job(
        _sync_and_alert,
        "interval",
        minutes=settings.sync_interval_minutes,
        id="sync",
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
    """Match root against rule (prefix). Normalize path separators and case for cross-platform."""
    if not root or not rule:
        return False
    root_n = root.replace("\\", "/").strip().lower()
    rule_n = rule.replace("\\", "/").strip().lower()
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
    workspace_rules: list[str]
    member_emails: list[str] = []
    created_by: str
    git_repos: list[str] = []
    auto_create_repo: bool = False
    repo_slug: str | None = None
    repo_provider: str | None = None  # 'gitlab' | 'github'; when auto_create_repo, which provider to use


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    git_repos: list[str] | None = None
    workspace_rules: list[str] | None = None
    member_emails: list[str] | None = None
    status: str | None = None


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
async def create_project(request: Request, body: ProjectCreate):
    """Create project. If auto_create_repo=true and repo_slug set, create GitLab or GitHub repo and inject Hook."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO projects (name, description, git_repos, workspace_rules, member_emails, created_by)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING *
            """,
            body.name,
            body.description,
            body.git_repos,
            body.workspace_rules,
            body.member_emails,
            body.created_by,
        )
    project_id = row["id"]
    collector_url = str(request.base_url).rstrip("/")
    provider = (body.repo_provider or "gitlab").lower() if body.auto_create_repo and body.repo_slug else None

    if provider == "github":
        from github_client import GitHubError, github_client

        if github_client.is_configured():
            try:
                gh = github_client.create_repo(
                    name=body.name,
                    repo_slug=body.repo_slug,
                    description=body.description or "",
                    private=True,
                )
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE projects SET repo_provider=$1, github_repo_full_name=$2,
                            repo_url=$3, repo_ssh_url=$4, git_repos=$5, updated_at=NOW()
                        WHERE id=$6
                        """,
                        "github",
                        gh.repo_full_name,
                        gh.repo_url,
                        gh.repo_ssh_url,
                        [gh.repo_url],
                        project_id,
                    )
                github_client.push_initial_commit(
                    gh.repo_full_name,
                    collector_url=collector_url,
                    project_id=project_id,
                    branch=gh.default_branch,
                )
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE projects SET hook_initialized=TRUE, updated_at=NOW() WHERE id=$1",
                        project_id,
                    )
            except GitHubError as exc:
                log.warning("GitHub repo create failed for project %s: %s", project_id, exc)
    elif provider == "gitlab":
        from gitlab_client import GitLabError, gitlab_client

        if gitlab_client.is_configured():
            try:
                gl = gitlab_client.create_project(
                    name=body.name,
                    path_slug=body.repo_slug,
                    description=body.description or "",
                )
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE projects SET repo_provider=$1, gitlab_project_id=$2, repo_url=$3, repo_ssh_url=$4,
                            git_repos=$5, updated_at=NOW()
                        WHERE id=$6
                        """,
                        "gitlab",
                        gl.gitlab_project_id,
                        gl.repo_url,
                        gl.repo_ssh_url,
                        [gl.repo_url],
                        project_id,
                    )
                gitlab_client.push_initial_commit(
                    gl.gitlab_project_id,
                    collector_url=collector_url,
                    project_id=project_id,
                )
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE projects SET hook_initialized=TRUE, updated_at=NOW() WHERE id=$1",
                        project_id,
                    )
                if body.member_emails:
                    gitlab_client.add_members(gl.gitlab_project_id, body.member_emails)
            except GitLabError as exc:
                log.warning("GitLab repo create failed for project %s: %s", project_id, exc)

    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM projects WHERE id=$1", project_id)
    return dict(row)


@app.get("/api/projects/whitelist")
async def get_projects_whitelist():
    """Return active projects' workspace rules for Hook whitelist check (no API key)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, workspace_rules, member_emails, updated_at
            FROM projects WHERE status='active' ORDER BY id
            """
        )
    if not rows:
        version = ""
        rules = []
    else:
        latest = max(r["updated_at"] for r in rows)
        version = latest.isoformat().replace("+00:00", "Z") if hasattr(latest, "isoformat") else str(latest)
        rules = [
            {
                "project_id": r["id"],
                "project_name": r["name"],
                "workspace_rules": list(r["workspace_rules"] or []),
                "member_emails": list(r["member_emails"] or []),
            }
            for r in rows
        ]
    return {"version": version, "rules": rules}


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
    """Project summary: cost (session count, duration), participants, Git contributions."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        proj = await conn.fetchrow("SELECT * FROM projects WHERE id=$1", project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    async with pool.acquire() as conn:
        cost_row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS session_count, COALESCE(SUM(duration_seconds), 0)::bigint AS total_duration_seconds
            FROM agent_sessions WHERE project_id=$1
            """,
            project_id,
        )
        participants = await conn.fetch(
            """
            SELECT user_email, COUNT(*) AS session_count, COALESCE(SUM(duration_seconds), 0)::bigint AS total_seconds
            FROM agent_sessions WHERE project_id=$1 GROUP BY user_email ORDER BY total_seconds DESC
            """,
            project_id,
        )
        contributions = await conn.fetch(
            """
            SELECT author_email, commit_date, commit_count, lines_added, lines_removed, files_changed
            FROM git_contributions WHERE project_id=$1 ORDER BY commit_date DESC, author_email
            """,
            project_id,
        )
    return {
        "project": dict(proj),
        "session_count": cost_row["session_count"] or 0,
        "total_duration_seconds": cost_row["total_duration_seconds"] or 0,
        "participants": [
            {
                "user_email": r["user_email"],
                "session_count": r["session_count"],
                "total_seconds": r["total_seconds"],
            }
            for r in participants
        ],
        "contributions": [
            {
                "author_email": r["author_email"],
                "commit_date": r["commit_date"].isoformat() if hasattr(r["commit_date"], "isoformat") else str(r["commit_date"]),
                "commit_count": r["commit_count"],
                "lines_added": r["lines_added"],
                "lines_removed": r["lines_removed"],
                "files_changed": r["files_changed"],
            }
            for r in contributions
        ],
    }


@app.put("/api/projects/{project_id}", dependencies=[Depends(require_api_key)])
async def update_project(project_id: int, body: ProjectUpdate):
    pool = await get_pool()
    updates: list[str] = []
    params: list = []
    idx = 1
    if body.name is not None:
        updates.append(f"name=${idx}")
        params.append(body.name)
        idx += 1
    if body.description is not None:
        updates.append(f"description=${idx}")
        params.append(body.description)
        idx += 1
    if body.git_repos is not None:
        updates.append(f"git_repos=${idx}")
        params.append(body.git_repos)
        idx += 1
    if body.workspace_rules is not None:
        updates.append(f"workspace_rules=${idx}")
        params.append(body.workspace_rules)
        idx += 1
    if body.member_emails is not None:
        updates.append(f"member_emails=${idx}")
        params.append(body.member_emails)
        idx += 1
    if body.status is not None:
        updates.append(f"status=${idx}")
        params.append(body.status)
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


@app.post("/api/projects/{project_id}/reinject-hook", dependencies=[Depends(require_api_key)])
async def reinject_hook(request: Request, project_id: int):
    """Re-inject Hook files into the project's GitLab or GitHub repository."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, repo_provider, gitlab_project_id, github_repo_full_name FROM projects WHERE id=$1",
            project_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    collector_url = str(request.base_url).rstrip("/")

    if row.get("repo_provider") == "github":
        from github_client import GitHubError, github_client

        full_name = row.get("github_repo_full_name")
        if not full_name:
            raise HTTPException(
                status_code=400,
                detail="Project has no GitHub repository; create one first or link an existing repo.",
            )
        if not github_client.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GitHub not configured; set GITHUB_TOKEN.",
            )
        try:
            github_client.inject_hook_files(
                full_name,
                collector_url=collector_url,
                project_id=project_id,
            )
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE projects SET hook_initialized=TRUE, updated_at=NOW() WHERE id=$1",
                    project_id,
                )
        except GitHubError as exc:
            log.warning("Reinject hook failed for project %s: %s", project_id, exc)
            raise HTTPException(status_code=502, detail=f"GitHub error: {exc!s}") from exc
    else:
        from gitlab_client import GitLabError, gitlab_client

        gl_id = row.get("gitlab_project_id")
        if not gl_id:
            raise HTTPException(
                status_code=400,
                detail="Project has no GitLab repository; create one first or link an existing repo.",
            )
        if not gitlab_client.is_configured():
            raise HTTPException(
                status_code=503,
                detail="GitLab not configured; set GITLAB_URL, GITLAB_TOKEN, GITLAB_GROUP_ID.",
            )
        try:
            gitlab_client.inject_hook_files(
                gitlab_project_id=gl_id,
                collector_url=collector_url,
                project_id=project_id,
            )
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE projects SET hook_initialized=TRUE, updated_at=NOW() WHERE id=$1",
                    project_id,
                )
        except GitLabError as exc:
            log.warning("Reinject hook failed for project %s: %s", project_id, exc)
            raise HTTPException(status_code=502, detail=f"GitLab error: {exc!s}") from exc
    return {"ok": True, "message": "Hook files re-injected."}


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
        async with pool.acquire() as conn:
            agg = await conn.fetchrow(
                """
                SELECT hook_adopted, total_score, rank, score_breakdown,
                       lines_added, lines_removed, commit_count, files_changed,
                       session_duration_hours, agent_requests
                FROM contribution_scores
                WHERE user_email = $1 AND project_id IS NULL AND period_type = $2 AND period_key = $3
                """,
                email,
                period_type,
                period_key,
            )
            proj_rows = await conn.fetch(
                """
                SELECT c.project_id, p.name AS project_name, c.total_score
                FROM contribution_scores c
                JOIN projects p ON p.id = c.project_id
                WHERE c.user_email = $1 AND c.period_type = $2 AND c.period_key = $3 AND c.project_id IS NOT NULL
                ORDER BY c.total_score DESC
                """,
                email,
                period_type,
                period_key,
            )
        if not agg:
            return {
                "user_email": email,
                "period_type": period_type,
                "period_key": period_key,
                "hook_adopted": False,
                "total_score": 0,
                "rank": None,
                "score_breakdown": {},
                "raw": {"lines_added": 0, "commit_count": 0, "session_duration_hours": 0, "agent_requests": 0, "files_changed": 0},
                "projects": [],
            }
        raw = dict(agg)
        score_breakdown = dict(agg["score_breakdown"] or {})
        return {
            "user_email": email,
            "period_type": period_type,
            "period_key": period_key,
            "hook_adopted": bool(agg["hook_adopted"]),
            "total_score": float(agg["total_score"]),
            "rank": agg["rank"],
            "score_breakdown": {k: float(v) for k, v in score_breakdown.items()},
            "raw": {
                "lines_added": raw.get("lines_added", 0),
                "commit_count": raw.get("commit_count", 0),
                "session_duration_hours": float(raw.get("session_duration_hours") or 0),
                "agent_requests": raw.get("agent_requests", 0),
                "files_changed": raw.get("files_changed", 0),
            },
            "projects": [
                {"project_id": r["project_id"], "project_name": r["project_name"], "total_score": float(r["total_score"])}
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
    period_key: str = Query(..., description="e.g. 2026-W08"),
    hook_only: bool = Query(True, description="Only include hook_adopted=true"),
):
    """Leaderboard for the given period. hook_only=true (default) filters to members with Hook data."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if hook_only:
            rows = await conn.fetch(
                """
                SELECT user_email, rank, total_score, hook_adopted,
                       lines_added, commit_count, session_duration_hours, agent_requests, files_changed
                FROM contribution_scores
                WHERE period_type = $1 AND period_key = $2 AND project_id IS NULL AND hook_adopted = TRUE
                ORDER BY rank ASC NULLS LAST, total_score DESC
                """,
                period_type,
                period_key,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT user_email, rank, total_score, hook_adopted,
                       lines_added, commit_count, session_duration_hours, agent_requests, files_changed
                FROM contribution_scores
                WHERE period_type = $1 AND period_key = $2 AND project_id IS NULL
                ORDER BY rank ASC NULLS LAST, total_score DESC
                """,
                period_type,
                period_key,
            )
        snapshot = await conn.fetchrow(
            "SELECT created_at FROM leaderboard_snapshots WHERE period_type = $1 AND period_key = $2",
            period_type,
            period_key,
        )
    generated_at = snapshot["created_at"].isoformat() if snapshot and snapshot.get("created_at") else None
    return {
        "period_type": period_type,
        "period_key": period_key,
        "generated_at": generated_at,
        "entries": [
            {
                "rank": r["rank"],
                "user_email": r["user_email"],
                "total_score": float(r["total_score"]),
                "hook_adopted": bool(r["hook_adopted"]),
                "lines_added": r["lines_added"],
                "commit_count": r["commit_count"],
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
    """Normalize JSONB/dict for JSON response (asyncpg may return dict or custom type)."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    try:
        return dict(val)
    except (TypeError, ValueError):
        return {}


@app.get("/api/incentive-rules", dependencies=[Depends(require_api_key)])
async def list_incentive_rules(enabled_only: bool = Query(False)):
    """List incentive rules. enabled_only=true returns only enabled rules."""
    import asyncpg
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


# ─── 健康检查 ─────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=False)
