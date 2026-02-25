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
from fastapi import Depends, FastAPI, Header, HTTPException, Query
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


@app.post("/api/sessions", status_code=204)
async def receive_session(payload: SessionPayload):
    """接收 Hook 上报的会话结束事件"""
    from datetime import datetime, timezone

    pool = await get_pool()
    ended_dt = datetime.fromtimestamp(payload.ended_at, tz=timezone.utc)
    started_dt = None
    if payload.duration_seconds is not None:
        started_dt = datetime.fromtimestamp(
            payload.ended_at - payload.duration_seconds, tz=timezone.utc
        )

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO agent_sessions
                (conversation_id, user_email, machine_id, workspace_roots, started_at, ended_at, duration_seconds)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            ON CONFLICT (conversation_id) DO NOTHING
            """,
            payload.conversation_id,
            payload.user_email,
            payload.machine_id,
            payload.workspace_roots,
            started_dt,
            ended_dt,
            payload.duration_seconds,
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


# ─── 健康检查 ─────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=False)
