# Requirements: Cursor Admin 核心平台

> **目标**：为 Sierac-tm 提供基础数据采集、持久化、告警与管理端 API，作为贡献可视化与激励平台的数据底座。  
> **优先级**：P0（已实现，持续维护与扩展）  
> **预估工作量**：已实现；后续迭代 2–5 天/次

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-core/requirements.md`
- design: `.kiro/specs/cursor-admin-core/design.md`
- tasks: `.kiro/specs/cursor-admin-core/tasks.md`
- status: `.kiro/specs/SPEC_TASKS_SCAN.md`

---

## 1. 背景与动机

### 1.1 定位

Cursor Admin 核心平台是 Sierac-tm 的**数据底座**，负责：

- 从 Cursor Admin API 定时拉取成员、用量、支出数据并落库。
- 接收 Hook 上报的会话事件，持久化会话记录（含项目归属）。
- 提供告警规则配置与触发通知。
- 为管理端与成员端提供统一的查询 API。

核心平台**不做**贡献度计算、排行榜、GitLab 集成——这些属于上层 spec（cursor-admin-projects、cursor-admin-incentives）。

### 1.2 与旧定位的区别

旧定位是「粗颗粒度用量管理系统」，新定位是**贡献可视化平台的数据底座**：

| 维度 | 旧 | 新 |
|------|----|----|
| 核心展示 | 用量、支出 | 贡献（用量作为效率参考） |
| 数据来源 | Cursor API + Hook | Cursor API + Hook + Git（后两者由上层 spec 扩展） |
| 核心实体 | 成员 + 工作目录 | **项目** + 成员 + 贡献 |

---

## 2. 用户故事

### 2.1 作为管理员——用量与支出

**故事**：查看团队成员的 Cursor 用量与支出，并设置超阈值告警。

**验收标准**：
- [x] 按成员、日期范围查看每日用量（Agent/Chat/Tab 请求、代码行等）。
- [x] 查看当前计费周期各成员支出。
- [x] 新建/编辑/删除告警规则（指标、阈值、通知渠道）。
- [x] 告警触发后写入历史，同一规则有冷却期（1 小时）。

### 2.2 作为管理员——会话数据

**故事**：查看成员的 Agent 会话记录（工作目录、时长），作为项目参与的补充信号。

**验收标准**：
- [x] 按用户、工作目录、时间范围查询会话汇总与明细。
- [x] 会话数据来自 Hook 上报（`POST /api/sessions`）。
- [x] 会话记录含 `project_id`（由 cursor-admin-projects 扩展，NULL 表示未归属）。

---

## 3. 功能需求

### FR-1：Cursor API 数据同步

- 定时拉取（默认每小时）：成员列表、每日用量、支出快照。
- 幂等写入：按唯一键（email+day、email+计费周期）做 upsert。
- 同步失败不影响服务启动；日志记录错误。

### FR-2：Hook 会话接收

- `POST /api/sessions`：接收 Hook 上报的会话结束事件。
- 字段：`conversation_id`（唯一键）、`user_email`、`machine_id`、`workspace_roots`、`ended_at`、`duration_seconds`、`project_id`（可选）。
- 重复上报（相同 conversation_id）忽略。
- 若 payload 无 `project_id`，Collector 根据 `workspace_roots` 匹配 `projects` 表补填。

### FR-3：告警

- 规则存储于 `alert_rules`；支持启用/停用。
- 通知渠道：邮件（SMTP）、Webhook（企业微信/钉钉）。
- 每次同步后执行告警检测；冷却期内不重复触发。
- 触发记录写入 `alert_events`。

### FR-4：查询 API

- 所有管理端 API 需 `x-api-key` 鉴权。
- 提供：`/api/members`、`/api/usage/daily`、`/api/usage/spend`、`/api/sessions`、`/api/sessions/summary`、`/api/alerts/rules`、`/api/alerts/events`。
- 支持分页与筛选。

### FR-5：健康检查

- `GET /health`：返回服务状态，无需鉴权。

---

## 4. 非功能需求

- **持久化**：PostgreSQL；迁移为 SQL 文件幂等执行（`db/migrations/`）。
- **安全**：API 密钥从环境变量读取，不写死代码；Hook 上报接口不暴露敏感信息。
- **可维护性**：日志使用标准库 logging；配置集中（`.env` + `config.py`）。
- **依赖管理**：Python 使用 Poetry；Node 使用 npm。

---

## 5. 约束与假设

- 依赖 Cursor Team/Enterprise 的 Admin API；拉取频率受 Cursor 限速约束。
- 单团队使用；未来多租户时表结构可扩展 `tenant_id`。
- 核心平台不包含贡献度计算逻辑（由 cursor-admin-incentives 负责）。

---

## 6. 依赖

- **外部**：Cursor Admin API、SMTP/Webhook 通知服务。
- **内部**：cursor-admin-hooks（上报契约一致）；cursor-admin-projects（projects 表、project_id 扩展）。

---

**维护者**: 团队  
**最后更新**: 2026-02-26  
**状态**: 已实现，持续维护
