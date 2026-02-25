# Requirements: Cursor Admin 核心平台

> **目标**：为 Cursor Team Plan 管理员提供粗颗粒度用量统计、支出管理、告警与工作目录/会话可见性。  
> **优先级**：P0  
> **预估工作量**：已实现，维护与扩展 5–10 天/迭代

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-core/requirements.md`
- design: `.kiro/specs/cursor-admin-core/design.md`
- tasks: `.kiro/specs/cursor-admin-core/tasks.md`
- status: `.kiro/specs/SPEC_TASKS_SCAN.md`

---

## 1. 背景与动机

### 1.1 当前问题

- 管理员需要按用户查看 Cursor 用量与支出，并设置告警。
- 需要知道成员「在哪个工作目录、工作了多久」，Cursor 官方 API 不提供，需通过 Hooks 补足。
- 需要粗颗粒度管控（不细到每次工具调用），避免大量 token 与存储成本。

### 1.2 设计目标

- 统一从 Cursor Admin API 拉取用量与支出，落库并供管理端查询与告警。
- 接收 Hook 上报的会话结束事件，持久化工作目录与时长，支持按用户/目录/时间汇总。
- 支持可配置告警规则（邮件、Webhook），并与未来激励扩展数据同源。

---

## 2. 用户故事

### 2.1 作为团队管理员

**故事 1**：用量总览  
作为管理员，我希望按成员与日期查看 Agent/Chat/Tab 请求量、代码行数等，这样我可以了解团队使用情况。

**验收标准**：
- [ ] 支持按成员、日期范围筛选每日用量。
- [ ] 展示趋势图与按用户汇总表。
- [ ] 数据来源于 Cursor Admin API 同步结果。

**故事 2**：支出与告警  
作为管理员，我希望查看本计费周期各成员支出，并设置超阈值告警（邮件/Webhook），这样我可以控制成本并及时获知异常。

**验收标准**：
- [ ] 展示当前周期支出、按量请求数、月度上限。
- [ ] 支持新建/编辑/删除告警规则（指标、范围、阈值、通知渠道）。
- [ ] 告警触发后写入历史并可查看；同一规则有冷却（如 1 小时）。

**故事 3**：工作目录与时长  
作为管理员，我希望看到每个成员在哪些工作目录下进行了多少会话、累计时长，这样我可以做粗颗粒度活跃度与投入分析。

**验收标准**：
- [ ] 支持按用户、工作目录、时间范围查询会话汇总（会话数、总时长、最近活跃）。
- [ ] 支持会话明细分页查询。
- [ ] 数据来源于 Hook 上报的 `/api/sessions` 写入结果。

---

## 3. 功能需求

### 3.1 数据同步

#### FR-1：成员与用量同步

**需求**：从 Cursor Admin API 定时拉取成员列表、每日用量、支出快照，写入本系统数据库。

**验收标准**：
- [ ] 成员：`/teams/members` → `members` 表，支持按 email 唯一更新。
- [ ] 每日用量：`/teams/daily-usage-data` → `daily_usage` 表，按 email+day 幂等。
- [ ] 支出：`/teams/spend` → `spend_snapshots` 表，按 email+计费周期幂等。
- [ ] 同步间隔可配置（如每小时）；遵守 Cursor API 建议拉取频率。

#### FR-2：会话数据接收

**需求**：接收 Hook 上报的会话结束事件，写入 `agent_sessions` 表。

**验收标准**：
- [ ] 接口：`POST /api/sessions`，Body 见 cursor-admin-hooks design。
- [ ] 字段：conversation_id、user_email、machine_id、workspace_roots、ended_at、duration_seconds。
- [ ] conversation_id 唯一，重复上报忽略。

### 3.2 告警

#### FR-3：告警规则与执行

**需求**：支持按指标（如每日 Agent 请求数、支出）与范围（用户/团队）配置阈值，超阈值时触发通知并记录历史。

**验收标准**：
- [ ] 规则存储于 `alert_rules`，支持启用/停用。
- [ ] 通知渠道：邮件（SMTP）、Webhook（企业微信/钉钉等）。
- [ ] 每次同步后执行告警检测；同一规则冷却期内不重复触发。
- [ ] 触发记录写入 `alert_events`，管理端可查历史。

### 3.3 管理端 API 与 UI

#### FR-4：查询 API

**需求**：管理端通过带 x-api-key 的 GET 请求获取成员、用量、支出、会话、告警规则与历史。

**验收标准**：
- [ ] 所有查询 API 需校验 `x-api-key`，与配置的 `INTERNAL_API_KEY` 一致。
- [ ] 提供：/api/members, /api/usage/daily, /api/usage/spend, /api/sessions, /api/sessions/summary, /api/alerts/rules, /api/alerts/events；支持分页与筛选。

#### FR-5：管理端页面

**需求**：Web 端提供用量总览、工作目录与时长、支出管理、告警配置、告警历史五个功能页面。

**验收标准**：
- [ ] 用量总览：筛选、趋势图、按用户汇总表。
- [ ] 工作目录：汇总视图 + 会话明细分页。
- [ ] 支出管理：本周期支出列表与搜索。
- [ ] 告警配置：规则 CRUD、通知渠道配置。
- [ ] 告警历史：触发记录列表。

---

## 4. 非功能需求

### NFR-1：数据持久化

- 使用 PostgreSQL；迁移为 SQL 文件幂等执行。
- 备份与恢复方式在部署文档中说明。

### NFR-2：安全

- API 密钥不写死代码，从环境变量或配置文件读取。
- Hook 上报接口不暴露敏感信息；仅接收会话级摘要。

### NFR-3：可维护性

- 日志使用标准库 logging；关键步骤有日志。
- 配置集中（环境变量或 config），便于部署与切换环境。

---

## 5. 约束与假设

- **约束**：依赖 Cursor Team/Enterprise 的 Admin API 与 Hooks 能力；拉取频率受 Cursor 限速约束。
- **假设**：单团队使用；未来多租户时表结构可扩展 tenant_id。

---

## 6. 依赖

- **外部**：Cursor Admin API、Cursor Analytics API（若用）、SMTP/Webhook 通知。
- **内部**：cursor-admin-hooks（上报契约一致）、db/migrations。

---

## 7. 参考文档

- `docs/ARCHITECTURE.md`
- `docs/cursor-team-admin-agent-visibility.md`
- `.kiro/specs/cursor-admin-hooks/design.md`（会话上报契约）

---

**维护者**: 团队  
**最后更新**: 2026-02-25
