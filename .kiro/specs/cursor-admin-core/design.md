# Design: Cursor Admin 核心平台

> **目标**：定义采集服务、数据模型、API 与管理端的技术设计。  
> **状态**：已完成（与当前实现对齐）  
> **最后更新**：2026-02-25

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-core/requirements.md`
- design: `.kiro/specs/cursor-admin-core/design.md`
- tasks: `.kiro/specs/cursor-admin-core/tasks.md`

---

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│  Cursor Platform (Admin API / Analytics API)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS, Basic Auth
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Collector (FastAPI)                                              │
│  ├── POST /api/sessions     ← Hook 上报                           │
│  ├── GET  /api/members, /api/usage/*, /api/sessions, /api/alerts │
│  ├── 定时任务：sync (members → daily_usage → spend)              │
│  └── 定时任务：sync 后 run check_alerts                           │
└────────────────────────────┬────────────────────────────────────┘
                             │ asyncpg
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                      │
│  members | daily_usage | spend_snapshots | agent_sessions |       │
│  alert_rules | alert_events                                       │
└─────────────────────────────────────────────────────────────────┘
                             ▲
                             │ x-api-key, GET
┌────────────────────────────┴────────────────────────────────────┐
│  Web (React + Vite) → Nginx 反向代理 /api → Collector            │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件

- **cursor_api.py**：Cursor API 客户端（get_members, get_daily_usage, get_spend 等），唯一出口。
- **sync.py**：sync_members、sync_daily_usage、sync_spend；由 main 启动时与定时任务调用。
- **alerts.py**：check_alerts 读取 alert_rules 与当前数据，超阈值则 dispatch_alert（邮件/Webhook）并写 alert_events。
- **main.py**：FastAPI 应用、/api/sessions 接收、查询 API、定时调度（APScheduler）。
- **database.py**：asyncpg 连接池、init_db 执行 migrations。

### 1.3 依赖与工具

- **Collector** 使用 **Poetry** 管理依赖：`cursor-admin/collector/pyproject.toml` + `poetry.lock`；Python ^3.10。
- Ruff（lint/format）与 pytest（asyncio_mode=auto）配置于同一 `pyproject.toml`；Docker 构建通过 Poetry 安装生产依赖。

---

## 2. 数据模型（表）

- **members**：user_id, email, name, role, is_removed, synced_at.
- **daily_usage**：email, day, agent_requests, chat_requests, composer_requests, total_tabs_*, total_lines_*, usage_based_reqs, most_used_model, is_active, synced_at；UNIQUE(email, day).
- **spend_snapshots**：email, billing_cycle_start, spend_cents, fast_premium_requests, monthly_limit_dollars, synced_at；UNIQUE(email, billing_cycle_start).
- **agent_sessions**：conversation_id(UNIQUE), user_email, machine_id, workspace_roots(ARRAY), primary_workspace(GENERATED), started_at, ended_at, duration_seconds, created_at.
- **alert_rules**：name, metric, scope, target_email, threshold, notify_channels(JSONB), enabled.
- **alert_events**：rule_id, triggered_at, metric_value, threshold, detail(JSONB).

详见 `cursor-admin/db/migrations/001_init.sql`。

---

## 3. API 契约

### 3.1 Hook 上报（入）

- **POST /api/sessions**  
  Body: `{ "event", "conversation_id", "user_email", "machine_id", "workspace_roots", "ended_at", "duration_seconds"? }`  
  Response: 204 No Content（无鉴权，内网或 VPN 暴露）。

### 3.2 管理端查询（出）

- 所有 GET /api/* 需 Header `x-api-key: <INTERNAL_API_KEY>`，否则 401。
- 分页：page, page_size；筛选：email, start, end, workspace 等，见 main.py 中路由。

---

## 4. 配置

- 环境变量：DATABASE_URL, CURSOR_API_TOKEN, CURSOR_API_URL, SYNC_INTERVAL_MINUTES, INTERNAL_API_KEY, SMTP_*, DEFAULT_WEBHOOK_URL 等，见 `.env.example`。
- 配置集中于 `collector/config.py`（pydantic-settings）。

---

## 5. 错误处理

- Cursor API 调用失败：记录日志，同步任务继续其他步骤或下次重试。
- Hook 上报写入失败：记录日志，返回 204 避免 Hook 端重试阻塞 Cursor。
- 告警发送失败：记录日志，alert_events 仍写入，便于排查。

---

## 6. 测试策略

- 单元：sync 逻辑（mock cursor_api）、alerts 规则匹配（mock DB）。
- 集成：API 路由（TestClient）、DB 使用测试库或 testcontainers。
- E2E：部署后 curl/浏览器验证关键路径。

---

## 7. 与 Hooks、激励的集成

- **Hooks**：仅通过 POST /api/sessions 契约交互；见 cursor-admin-hooks design。
- **激励扩展**：未来 contribution_scores / leaderboard 表与任务在 cursor-admin-incentives 中设计；本模块仅保证 daily_usage、agent_sessions、spend 数据完整可用。

---

## 8. 参考文档

- `docs/ARCHITECTURE.md`
- `cursor-admin/collector/main.py`、`sync.py`、`alerts.py`

---

**维护者**: 团队  
**最后更新**: 2026-02-25
