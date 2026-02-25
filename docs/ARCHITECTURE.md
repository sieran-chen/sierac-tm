# Sierac-tm / Cursor Admin 总体架构

> **版本**: v1.0.0  
> **状态**: 架构真源  
> **最后更新**: 2026-02-25  
> **适用范围**: 文档驱动开发、Spec 设计、集成边界

---

## 一、项目定位

**Sierac-tm** 是基于 Cursor Team Plan 的**团队用量与可见性管理**系统，面向管理员提供：

1. **粗颗粒度用量**：按用户统计用量与支出，支持告警。
2. **工作目录与时长**：通过 Cursor Hooks 采集「在哪个目录、会话时长」，每会话 1 条上报。
3. **管控能力**：支出上限、告警规则、仓库封禁（依托 Cursor Admin API）。
4. **扩展方向**：演进为**团队激励管理工具**——贡献度排行、评分、与激励挂钩。

主体实现语言：**Python**（采集服务、同步、告警、API）；**TypeScript/React**（管理端）；**多语言 Hook**（Java 主推、Python 备选），对外协议统一（HTTP JSON）。

---

## 二、系统边界与上下文

```
                    ┌─────────────────────────────────────────┐
                    │         Cursor Platform                  │
                    │  (Admin API / Analytics API / Dashboard)  │
                    └──────────────────┬──────────────────────┘
                                       │ HTTPS, API Key
                                       ▼
┌──────────────┐              ┌───────────────────────────────────────┐
│ 成员机器      │   POST       │  Sierac-tm (本系统)                     │
│ Cursor IDE   │ ────────────►│  collector (FastAPI)                   │
│ + Hook       │  /api/       │    ├─ 接收 Hook 会话上报                 │
│ (Java/Python)│  sessions    │    ├─ 定时拉取 Cursor API → 落库         │
└──────────────┘              │    ├─ 告警检测与通知                     │
                              │    └─ 管理端查询 API                     │
                              │  db (PostgreSQL)                        │
                              │  web (React + Nginx)  ← 管理端          │
                              └───────────────────────────────────────┘
```

- **入**：Cursor Admin/Analytics API（拉取）、Hook 上报（推送）。
- **出**：邮件/Webhook 告警、管理端展示；未来扩展：激励排行与评分数据消费方。

---

## 三、包结构与技术选型

```
Sierac-tm/
├── cursor-admin/              # 主应用
│   ├── collector/             # 采集服务（Python, FastAPI）
│   │   ├── main.py            # 入口、API、定时任务
│   │   ├── sync.py            # Cursor API 同步
│   │   ├── alerts.py          # 告警检测与通知
│   │   ├── cursor_api.py      # Cursor API 客户端
│   │   ├── database.py        # 连接与迁移
│   │   └── config.py
│   ├── db/
│   │   └── migrations/        # SQL 迁移（幂等）
│   ├── hook/                  # 客户端 Hook（多语言）
│   │   ├── java/              # Java 实现（主推）
│   │   ├── cursor_hook.py     # Python 实现（备选）
│   │   ├── install.sh | .ps1
│   │   └── hooks.json 模板
│   └── web/                   # 管理端（TypeScript, React, Vite）
│       └── src/
├── docs/                      # 架构与产品文档
├── .kiro/                     # Spec 文档（文档驱动）
│   └── specs/
├── .cursor/rules/             # Cursor 规则（本工程）
└── docker-compose.yml
```

| 层次       | 技术选型        | 说明 |
|------------|-----------------|------|
| 采集服务   | Python 3.12, FastAPI, asyncpg, APScheduler | 数据拉取与写入、告警逻辑适合 Python；异步 I/O |
| 管理端     | TypeScript, React, Vite, Tailwind, Recharts | 看板与配置 UI |
| Hook       | Java 11 (主) / Python 3 (备) | 团队主语言 Java；协议统一，多语言实现 |
| 数据库     | PostgreSQL 16  | 持久化；迁移为 SQL 文件幂等执行 |
| 部署       | Docker Compose | db + collector + web |

---

## 四、核心组件与数据流

### 4.1 数据流概览

```
Hook (stop 事件) ──► POST /api/sessions ──► agent_sessions 表
                                              (workspace_roots, duration, user_email)

Cursor Admin API ──► 定时任务 (sync) ──► members, daily_usage, spend_snapshots
                    (每小时)

告警任务 (sync 后) ──► 规则匹配 ──► alert_events + 邮件/Webhook 通知

管理端 ──► GET /api/* (x-api-key) ──► 查询 DB 展示
```

### 4.2 集成边界

| 能力           | 自建 | 集成           | 隔离位置 |
|----------------|------|----------------|----------|
| 采集 API、同步、告警 | ✅   |                | collector/*.py |
| Cursor API 调用 |      | ✅ Cursor 官方  | cursor_api.py |
| Hook 协议      | ✅   | Cursor Hooks 约定 | hook/* 多语言实现 |
| 管理端 UI      | ✅   |                | web/src |
| 数据库         | ✅   | PostgreSQL     | db/migrations |

**约束**：所有 Cursor API 调用必须经 `cursor_api.py`；Hook 与 collector 之间仅通过 HTTP JSON 契约通信（见 specs）。

---

## 五、扩展：团队激励管理（预留）

未来将本系统扩展为**团队激励管理工具**，与贡献度排行、评分挂钩。架构上需预留：

### 5.1 数据预留

- **现有表**已支持激励衍生：
  - `daily_usage`：按人按日 Agent/Chat/Tab、代码行数 → 可做「贡献度」原始指标。
  - `agent_sessions`：按人按目录会话数与时长 → 可做「活跃度」「专注度」。
  - `spend_snapshots`：支出 → 可与预算/效率结合。
- **扩展表**（后续 Spec 设计）建议：
  - `contribution_scores`：按周期（日/周/月）、按用户聚合的得分与维度（如：agent_usage_score, workspace_depth_score, line_contribution_score）。
  - `leaderboard_snapshots`：历史排行榜快照，供展示与审计。
  - `incentive_rules`：评分规则、权重、周期（与 alert_rules 类似但用于积分）。

### 5.2 服务扩展

- **Collector**：在现有 sync 之后增加「贡献度计算」任务（读 daily_usage / agent_sessions，写 contribution_scores）。
- **API**：新增 `/api/leaderboard`、`/api/scores` 等，管理端增加「排行」「我的得分」等页面。
- **Hook**：无需变更；激励依赖已有用量与会话数据。

### 5.3 原则

- 激励相关逻辑与「用量/告警」解耦：独立模块、独立 Spec（cursor-admin-incentives）。
- 评分规则可配置、可审计，避免硬编码。
- 排行与得分仅基于已采集的粗颗粒度数据，不引入细粒度 Hook。

---

## 六、文档与规范引用

| 查什么       | 去哪里 |
|--------------|--------|
| 架构决策     | 本文档 `docs/ARCHITECTURE.md` |
| Spec 规范    | `.kiro/SPEC_DOCUMENTATION_STANDARD.md` |
| Spec 总览    | `.kiro/specs/SPEC_TASKS_SCAN.md` |
| Cursor 可见性调研 | `docs/cursor-team-admin-agent-visibility.md` |

---

**维护者**: 团队  
**最后更新**: 2026-02-25
