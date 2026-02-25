# Tasks: Cursor Admin 核心平台

> **状态**：已完成（与当前实现一致）  
> **预估工作量**：已实现，后续为维护与扩展  
> **最后更新**：2026-02-25  
> **执行原则**：凡设计即交付；任务清单内不区分可选与必选。

---

## 进度概览

- **总任务数**：按下列 Phase 统计
- **已完成**：Phase 1–2 已实现
- **进行中**：无
- **未开始**：Phase 3 扩展（若有）

---

## 1. Phase 1：数据与同步（已完成）

### 1.1 数据库与迁移

- [x] 1.1.1 创建 `db/migrations/001_init.sql`，定义 members、daily_usage、spend_snapshots、agent_sessions、alert_rules、alert_events 表及索引
- [x] 1.1.2 collector 启动时调用 database.init_db() 幂等执行迁移

### 1.2 Cursor API 与同步

- [x] 1.2.1 实现 cursor_api.py：get_members、get_daily_usage、get_spend，Basic Auth
- [x] 1.2.2 实现 sync.py：sync_members、sync_daily_usage、sync_spend，写入 DB 并 ON CONFLICT 更新
- [x] 1.2.3 main.py 启动时执行一次 run_full_sync；APScheduler 按 SYNC_INTERVAL_MINUTES 定时执行 run_full_sync

### 1.3 会话接收

- [x] 1.3.1 实现 POST /api/sessions：解析 Body，写入 agent_sessions（conversation_id 唯一则忽略重复）
- [x] 1.3.2 与 cursor-admin-hooks 契约一致（见 hooks design）

---

## 2. Phase 2：告警与管理端（已完成）

### 2.1 告警

- [x] 2.1.1 实现 alert_rules 表与 alert_events 表
- [x] 2.1.2 实现 alerts.py：check_alerts（按规则读 daily_usage/spend_snapshots，超阈值则 dispatch_alert）
- [x] 2.1.3 通知渠道：邮件（SMTP）、Webhook；同一规则冷却（如 1h）内不重复触发
- [x] 2.1.4 main 在 sync 后调用 check_alerts
- [x] 2.1.5 实现 /api/alerts/rules CRUD、/api/alerts/events 列表

### 2.2 查询 API

- [x] 2.2.1 所有 GET /api/* 校验 x-api-key
- [x] 2.2.2 实现 /api/members, /api/usage/daily, /api/usage/spend, /api/sessions, /api/sessions/summary

### 2.3 管理端 Web

- [x] 2.3.1 用量总览页：筛选、趋势图、按用户汇总
- [x] 2.3.2 工作目录页：汇总视图 + 会话明细分页
- [x] 2.3.3 支出管理页：本周期支出列表与搜索
- [x] 2.3.4 告警配置页：规则 CRUD、通知渠道
- [x] 2.3.5 告警历史页：触发记录列表
- [x] 2.3.6 Nginx 反向代理 /api 到 collector；前端通过 VITE_API_BASE 与 VITE_API_KEY 调用

---

## 3. Phase 3：后续扩展（按需）

### 3.1 测试与质量

- [x] 3.1.1 为 sync、alerts、API 路由补充单元/集成测试
- [x] 3.1.2 配置 Ruff（pyproject.toml）并通过

### 3.2 激励扩展预留

- [ ] 3.2.1 当 cursor-admin-incentives spec 启动时，在 collector 中增加「贡献度计算」任务（读 daily_usage/agent_sessions，写 contribution_scores）；不在此 spec 内实现具体评分逻辑

---

## 4. 验收清单

### 4.1 功能验收

- [x] 同步后 members、daily_usage、spend_snapshots 有数据（需有效 Cursor API Token）
- [x] Hook 上报后 agent_sessions 有对应记录
- [x] 告警规则可配置并触发后写入 alert_events、发送通知（需配置 SMTP 或 Webhook）
- [x] 管理端五页可访问且数据正确展示

### 4.2 部署验收

- [x] docker-compose up 后 db、collector、web 正常；/health 返回 ok

---

## 5. 依赖与阻塞

- 依赖 Cursor Team/Enterprise Admin API 与 Hooks 能力。
- 依赖 cursor-admin-hooks 上报格式与 POST /api/sessions 契约一致。

---

## 6. 参考文档

- `.kiro/specs/cursor-admin-core/requirements.md`
- `.kiro/specs/cursor-admin-core/design.md`
- `docs/ARCHITECTURE.md`

---

**维护者**: 团队  
**最后更新**: 2026-02-25
