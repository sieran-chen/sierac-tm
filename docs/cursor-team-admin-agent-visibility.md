# Cursor Team Plan 管理员：粗颗粒度用量、告警与工作目录可见性

## 1. 需求澄清（优化后）

| 需求 | 说明 | 颗粒度 |
|------|------|--------|
| **按用户用量统计 + 告警** | 每人用了多少（请求/ token/ 费用），超阈值告警 | 粗：按用户/按日或按周期 |
| **工作目录 + 工作时长** | 在哪个目录（workspace）工作了多久 | 粗：按会话结束上报，每会话 1 条 |
| **管控级可见性** | 支出控制、分组查看、策略（如封禁仓库） | 粗：不采集单次工具调用/单次编辑 |

**不采用**：细颗粒度方案（如逐条工具调用、每次文件编辑的 OTEL 轨迹），以避免大量 token/存储与处理成本。

---

## 2. 官方能力与缺口

### 2.1 用量统计 + 告警（官方已覆盖大部分）

| 能力 | 说明 | 适用场景 |
|------|------|----------|
| **Admin API** | `/teams/spend` 按用户支出；`/teams/daily-usage-data` 按日按用户用量；`/teams/filtered-usage-events` 按事件查询用量/费用 | 自建看板、定时拉取、**自定义告警** |
| **Analytics API**（Enterprise） | 按用户/按日：agent-edits、tabs、models、DAU、leaderboard 等 | 用量分析、排行、报表 |
| **Dashboard 内置** | 用量、支出、**邮件支出告警**（个人/团队阈值） | 开箱即用告警 |
| **Billing Groups**（Enterprise） | 按组查看支出、预算告警、与目录同步 | 粗颗粒度按组管控 |

**结论**：**按用户用量统计与告警**可直接基于 **Admin API + 自带 Dashboard 告警** 实现；若要接入自有监控栈，可用 **cursor-admin-api-exporter** 暴露 Prometheus，再用 **Grafana + Alertmanager** 做自定义告警。

### 2.2 工作目录 + 工作时长（官方 API 无此数据）

- **Admin API / Analytics API** 均**不提供**「在哪个工作目录（workspace）」或「在某个目录下工作了多久」。
- **唯一可行方式**：用 **Hooks** 做**极简上报**——仅在一次 Agent 会话结束时（`stop` 事件）上报一条记录，包含：
  - `workspace_roots`（Cursor 在 stop 的 payload 中提供）
  - `conversation_id`（会话 id）
  - 结束时间；若需「工作时长」，可在本地用「会话开始」时间戳推算（见下节）。

这样**不会**产生大量事件，也不会消耗大量 token，属于粗颗粒度管控级。

### 2.3 粗颗粒度管控（官方已支持）

- **按用户支出上限**：Admin API `POST /teams/user-spend-limit`（Enterprise）。
- **按组预算与告警**：Billing Groups + 预算告警（Enterprise）。
- **仓库级策略**：Admin API `/settings/repo-blocklists/repos` 管理索引/上下文封禁。

---

## 3. 推荐方案总览（粗颗粒度）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  用量统计 + 告警（不写 Hook，零额外 token）                               │
│  • Cursor Dashboard 自带：用量 + 支出 + 邮件告警                          │
│  • 自定义告警：cursor-admin-api-exporter → Prometheus → Alertmanager   │
│  • 或定时轮询 Admin API / Analytics API，自建告警逻辑                    │
├─────────────────────────────────────────────────────────────────────────┤
│  工作目录 + 工作时长（极简 Hook，每会话 1 条）                            │
│  • 仅注册 stop（+ 可选「会话开始」）→ 上报 workspace_roots + 时长        │
│  • 自建小型「会话汇总」API + 管理端展示                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 方案一：按用户用量 + 告警（无需 Hook）

### 4.1 用 Cursor 自带能力

- **用量/支出**：Team 管理员在 [Dashboard](https://cursor.com/dashboard) 查看用量、支出、按成员花费。
- **告警**：在 Dashboard **Spending** 中设置**邮件支出告警**（个人/团队阈值），超限会邮件通知。

### 4.2 用 cursor-admin-api-exporter + Prometheus + Grafana（自定义告警）

- **仓库**：<https://github.com/matanbaruch/cursor-admin-api-exporter>
- **作用**：用 Admin API 拉取团队成员、每日用量、支出、token 等，以 **Prometheus metrics** 暴露。
- **部署示例**（Docker）：
  ```bash
  docker run -p 8080:8080 \
    -e CURSOR_API_TOKEN=your_token \
    -e CURSOR_API_URL=https://api.cursor.com \
    ghcr.io/matanbaruch/cursor-admin-api-exporter:latest
  ```
- **告警**：Prometheus 抓取该 exporter，在 **Alertmanager** 或 **Grafana** 中配置规则（例如某用户当日支出 > N 美元则告警），通过邮件/钉钉/企业微信等通知。

这样实现的是**粗颗粒度**的「每用户用量 + 告警」，不依赖任何 Hook，也不产生额外 token 消耗。

### 4.3 直接调 Admin API 自建看板/告警

- **按用户支出**：`POST /teams/spend`（分页、排序、搜索）。
- **按用户按日用量**：`POST /teams/daily-usage-data`（含 agentRequests、chatRequests、composerRequests、totalLinesAdded 等）。
- **按用户用量事件**：`POST /teams/filtered-usage-events`（按 `email`/`userId` 筛选，含 token、费用等）。

可写定时任务（如每小时一次，遵守 API 建议的拉取频率），将数据落库或入时序库，再在自建看板中展示，并实现「超阈值告警」。

---

## 5. 方案二：工作目录 + 工作时长（极简 Hook，粗颗粒度）

官方 API 无「工作目录」与「工作时长」，只能通过 **Hooks** 在**会话维度**补足，且**仅上报会话级摘要**，避免细颗粒度带来的 token/存储压力。

### 5.1 Hook 事件与 payload

- **`stop` 事件**：Agent 任务结束时会触发，payload 中通常包含：
  - `workspace_roots`：当前工作区根路径（数组）
  - `conversation_id`：会话 id
  - `hook_event_name`：如 `"stop"`
- **「工作时长」**：Cursor 若未在 stop 中提供 duration，可：
  - **方案 A**：只上报「在哪个目录、何时结束」；时长用「该用户该日在该 workspace 的 stop 次数」近似活跃度。
  - **方案 B**：增加对「会话开始」类事件（若有）或首条可用的 hook 的监听，在本地记录 `conversation_id + 开始时间`，在 `stop` 时计算 duration，**只上报一条汇总**（workspace_roots、conversation_id、开始/结束时间或 duration）。

### 5.2 极简 Hook 设计要点

- **仅注册**：`stop`（必选）；若需时长再选一个「会话开始」类 hook（视 Cursor 文档实际提供为准）。
- **上报内容**：仅会话级字段，例如：
  - `workspace_roots`、`conversation_id`、结束时间（及可选：开始时间或 duration）
  - 用户标识：若 payload 无则用本机用户/环境变量/预置 team user id，避免传大段上下文。
- **不采集**：工具调用内容、文件内容、prompt 全文、单次编辑等，保证粗颗粒度、低 token。

### 5.3 自建侧

- **接收端**：小型 HTTP 服务，接收 hook 上报，写入 DB（如按 user_id、workspace_root、date、session_count/duration 聚合）。
- **管理端**：按用户、时间范围、工作目录查看「在哪个目录工作了多久」（按会话数或总时长展示），无需展示单次操作。

这样实现的是**粗颗粒度**的「在哪个工作目录、工作了多久」，事件量约等于「Agent 会话数」，不会造成大量 token 消耗。

---

## 6. 不推荐：细颗粒度方案（仅作对比）

| 方案 | 颗粒度 | 问题 |
|------|--------|------|
| **cursor-otel-hook**（LangGuard-AI） | 每次工具调用、文件读/写、MCP、Shell 等全量上报 | 事件量极大，存储与 token 消耗高，不符合「粗颗粒度管控」需求 |
| 自建全量 Hook（多种事件） | 同左 | 同上 |

若未来有安全审计等**细粒度**需求，再考虑在限定范围（如仅部分成员或仅敏感项目）启用此类方案。

---

## 7. 建议总结（按你当前需求）

| 需求 | 推荐做法 | 是否用 Hook | Token/成本 |
|------|----------|-------------|------------|
| **按用户用量统计** | Admin API / Analytics API + Dashboard 或 cursor-admin-api-exporter | 否 | 无额外 |
| **用量/支出告警** | Dashboard 邮件告警 + 可选 Prometheus/Alertmanager 自定义规则 | 否 | 无额外 |
| **看到在哪个工作目录工作了多久** | 极简 Hook（仅 stop ± 会话开始）→ 自建会话汇总 API + 管理端 | 是（每会话 1 条） | 极低 |
| **粗颗粒度管控** | Billing Groups、user-spend-limit、repo-blocklists（Admin API） | 否 | 无额外 |

**实施顺序建议**：

1. **先做用量 + 告警**：用 Dashboard 和（可选）cursor-admin-api-exporter + Prometheus/Grafana，不写 Hook。
2. **再补「工作目录 + 时长」**：确认 Cursor 当前 `stop`（及是否有会话开始）payload 字段后，写极简 Hook + 小型接收服务 + 管理端展示。

这样整体是**粗颗粒度、管控级**的方案，避免细颗粒度带来的大量 token 与存储消耗。

---

*文档基于 Cursor 官方 Admin API、Analytics API、Hooks 文档及开源项目说明整理，实施前请以 Cursor 最新文档为准。*
