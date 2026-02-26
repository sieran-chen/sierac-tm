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
from database import close_pool, get_pool, init_db
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
    scheduler.start()
    log.info("Scheduler started, sync every %d min", settings.sync_interval_minutes)

    yield

    scheduler.shutdown()
    await close_pool()


async def _sync_and_alert():
    await run_full_sync()
    await check_alerts()


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
    """Create project. If auto_create_repo=true and repo_slug set, create GitLab repo and inject Hook."""
    from gitlab_client import GitLabError, gitlab_client

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

    if body.auto_create_repo and body.repo_slug and gitlab_client.is_configured():
        collector_url = str(request.base_url).rstrip("/")
        try:
            gl = gitlab_client.create_project(
                name=body.name,
                path_slug=body.repo_slug,
                description=body.description or "",
            )
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE projects SET gitlab_project_id=$1, repo_url=$2, repo_ssh_url=$3,
                        git_repos=$4, updated_at=NOW()
                    WHERE id=$5
                    """,
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
    """Re-inject Hook files into the project's GitLab repository."""
    from gitlab_client import GitLabError, gitlab_client

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, gitlab_project_id FROM projects WHERE id=$1", project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    if not row["gitlab_project_id"]:
        raise HTTPException(
            status_code=400,
            detail="Project has no GitLab repository; create one first or link an existing repo.",
        )
    if not gitlab_client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="GitLab not configured; set GITLAB_URL, GITLAB_TOKEN, GITLAB_GROUP_ID.",
        )
    collector_url = str(request.base_url).rstrip("/")
    try:
        gitlab_client.inject_hook_files(
            gitlab_project_id=row["gitlab_project_id"],
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


# ─── 健康检查 ─────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=False)
