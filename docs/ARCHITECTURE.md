# Sierac-tm / Cursor Admin 总体架构

> **版本**: v2.1.0  
> **状态**: 架构真源  
> **最后更新**: 2026-02-26  
> **适用范围**: 文档驱动开发、Spec 设计、集成边界

---

## 一、项目定位（v2.0 战略重定义）

**Sierac-tm** 是一个**以贡献可视化驱动团队积极性的 AI 团队管理平台**。

> **核心理念：让贡献被看见，让积极性自然生长。**

核心能力：

1. **项目立项与治理**：公司项目在平台注册后进入白名单，Hook 据此放行或拦截，确保公司 Token 只用于公司项目。
2. **贡献可视化**：多源融合（Cursor API + Git + Hook），展示成员在已立项项目上的代码产出、项目参与、AI 使用效率。
3. **激励闭环**：贡献度评分、排行榜、周期快照，与团队激励机制挂钩。
4. **用量与告警**：按用户统计用量与支出，支持告警（保留能力，作为效率参考而非核心展示）。

主体实现语言：**Python**（采集服务、同步、告警、API）；**TypeScript/React**（管理端）；**多语言 Hook**（Java 主推、Python 备选），对外协议统一（HTTP JSON）。

### 与旧定位的区别

| 维度 | 旧（用量监控） | 新（贡献可视化 + 治理） |
|------|---------------|------------------------|
| 看什么 | 请求数、Token、支出 | 代码产出、项目参与、效率 |
| 给谁看 | 管理员 | 管理员 + 成员自己 |
| 驱动什么 | 成本控制 | 积极性 + 合规（同一份数据，两种叙事） |
| 核心实体 | 成员 + 工作目录 | **项目** + 成员 + 贡献 |

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
│ + Hook       │  /api/       │    ├─ 项目立项 & 白名单管理               │
│ (Python)     │  sessions    │    ├─ GitLab 仓库创建 & Hook 注入        │
└──────────────┘              │    ├─ 接收 Hook 上报（含白名单校验）       │
                              │    ├─ 定时拉取 Cursor API → 落库         │
┌──────────────┐              │    ├─ 定时扫描 Git 仓库 → 代码贡献        │
│ GitLab       │  API v4      │    ├─ 贡献度计算（多源融合）              │
│ (仓库托管)   │ ◄───────────│    ├─ 告警检测与通知                     │
└──────────────┘              │    └─ 管理端 & 成员端查询 API             │
                              │  db (PostgreSQL)                        │
┌──────────────┐              │  web (React + Nginx)  ← 管理端 + 成员端  │
│ Git 仓库      │  clone/pull  └───────────────────────────────────────┘
│ (公司项目)    │ ◄───────────  git_sync.py 定时扫描
└──────────────┘
```

- **入**：Cursor Admin/Analytics API（拉取）、Hook 上报（推送）、Git 仓库（定时扫描）。
- **出**：GitLab API（仓库创建、Hook 注入、成员管理）、邮件/Webhook 告警、管理端展示、成员端「我的贡献」；贡献排行与评分。

---

## 三、包结构与技术选型

```
Sierac-tm/
├── cursor-admin/              # 主应用
│   ├── collector/             # 采集服务（Python, FastAPI）
│   │   ├── main.py            # 入口、API、定时任务
│   │   ├── sync.py            # Cursor API 同步
│   │   ├── git_sync.py        # Git 仓库贡献采集
│   │   ├── gitlab_client.py   # GitLab API 客户端（仓库创建、Hook 注入）
│   │   ├── alerts.py          # 告警检测与通知
│   │   ├── cursor_api.py      # Cursor API 客户端
│   │   ├── database.py        # 连接与迁移
│   │   ├── config.py
│   │   └── hook_templates/    # Hook 模板（立项时注入仓库）
│   ├── db/
│   │   └── migrations/        # SQL 迁移（幂等）
│   ├── hook/                  # Hook 模板源 + 全局安装脚本
│   │   ├── cursor_hook.py     # Python 实现
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
管理员立项 ──► POST /api/projects ──► projects 表（白名单）
                                        ↓
              gitlab_client.py ──► GitLab 创建仓库 + 注入 .cursor/ Hook
                                        ↓
              成员 clone 仓库 ──► Hook 自动生效
                                        ↓
Hook (beforeSubmitPrompt) ──► 检查白名单 ──► 匹配 → 放行 / 不匹配 → 拦截
Hook (stop 事件) ──► POST /api/sessions ──► agent_sessions 表（标记所属项目）

Git 仓库 ──► 定时扫描 (git log/diff) ──► git_contributions 表
              (已立项项目的仓库)            (commit、diff、按人按项目)

Cursor Admin API ──► 定时任务 (sync) ──► members, daily_usage, spend_snapshots
                    (每小时)

贡献度计算 ──► 融合 git_contributions + agent_sessions + daily_usage
              ──► contribution_scores 表

告警任务 (sync 后) ──► 规则匹配 ──► alert_events + 邮件/Webhook 通知

管理端 ──► GET /api/* (x-api-key) ──► 查询 DB 展示（按项目聚合）
成员端 ──► GET /api/my/* ──► 我的贡献、我的项目
```

### 4.2 集成边界

| 能力           | 自建 | 集成           | 隔离位置 |
|----------------|------|----------------|----------|
| 采集 API、同步、告警 | ✅   |                | collector/*.py |
| Cursor API 调用 |      | ✅ Cursor 官方  | **cursor_api.py 唯一** |
| GitLab 仓库管理 |      | ✅ GitLab API v4 | **gitlab_client.py 唯一** |
| Git 仓库采集   | ✅   | Git CLI        | **git_sync.py** |
| Hook 协议 + 模板 | ✅   | Cursor Hooks 约定 | hook/* + hook_templates/ |
| 管理端 UI      | ✅   |                | web/src |
| 数据库         | ✅   | PostgreSQL     | db/migrations |

**约束**：所有 Cursor API 调用必须经 `cursor_api.py`；所有 GitLab API 调用必须经 `gitlab_client.py`；Hook 与 collector 之间仅通过 HTTP JSON 契约通信。

---

## 五、核心实体：项目（Project）

**项目是平台的一等实体**。所有贡献数据、参与数据、治理策略都围绕「项目」组织。

### 5.1 项目立项流程

```
管理员「立项」→ 填写项目信息（名称、描述、成员、仓库 slug）
    → 平台自动在 GitLab 创建仓库（含 .cursor/ Hook 目录）
    → 自动添加成员到仓库（Developer 权限）
    → 白名单生效 → 成员 clone 仓库 → Hook 自动生效
    → Git 采集开始扫描该项目的仓库
    → 贡献数据自动归属到该项目
```

### 5.2 新增数据模型

| 表 | 说明 |
|----|------|
| `projects` | 已立项项目（名称、Git 仓库、工作目录规则、成员、状态） |
| `git_contributions` | Git 代码贡献（按人按项目按日：commit 数、增删行数、文件数） |
| `contribution_scores` | 贡献度得分（按人按项目按周期：多维度得分与总分） |
| `incentive_rules` | 评分规则（权重配置、周期、启用状态） |
| `leaderboard_snapshots` | 历史排行快照（可选，供审计与趋势） |

### 5.3 治理层

- Hook `beforeSubmitPrompt` 检查白名单 → 未立项项目拦截
- 贡献数据按项目聚合 → 管理员自然可见成员在哪些项目有产出
- 同一份数据：成员看到「我的贡献」（正向），管理员看到「贡献 + 合规」

### 5.4 原则

- 项目立项是 Phase 0，优先于贡献可视化和激励
- 激励逻辑与「用量/告警」解耦：独立模块、独立 Spec
- 评分规则可配置、可审计，避免硬编码
- Git 是贡献的第一数据源；Cursor API 是效率参考；Hook 是参与信号

### 5.5 激励模块实现

- **计算引擎**：`collector/contribution_engine.py`。从 `git_contributions`、`agent_sessions`、`daily_usage` 三源按周期聚合，按 `incentive_rules` 的权重与上限计算得分，写入 `contribution_scores`（含 per-project 与 aggregate 行）；仅 `hook_adopted=true` 的成员参与排名；写入 `leaderboard_snapshots` 快照。
- **触发时机**：APScheduler 定时任务（Asia/Shanghai）：每日 00:30（上一日）、每周一 01:00（上一周）、每月 1 日 01:30（上一月）；另支持 `POST /api/incentive-rules/{id}/recalculate` 手动重算。
- **API**：`GET /api/contributions/my`（成员端，支持 period_type/period_key 返回得分视图）、`GET /api/contributions/leaderboard`（管理端，hook_only 过滤）、`GET/POST/PUT/DELETE /api/incentive-rules` 与重算。
- **前端**：管理端「排行榜」页（周期选择、CSV 导出）、「激励规则」页（权重滑块、上限、重新计算）；成员端「我的贡献」页（得分卡、历史趋势、项目分布、Hook 状态提示）。E2E 验证清单见 `.kiro/specs/cursor-admin-incentives/E2E_VERIFICATION.md`。

---

## 六、文档与规范引用

| 查什么       | 去哪里 |
|--------------|--------|
| 架构决策     | 本文档 `docs/ARCHITECTURE.md` |
| Spec 规范    | `.kiro/SPEC_DOCUMENTATION_STANDARD.md` |
| Spec 总览    | `.kiro/specs/SPEC_TASKS_SCAN.md` |
| 项目立项设计  | `.kiro/specs/cursor-admin-projects/design.md` |
| 旧文档归档   | `docs/_archive/` |

---

**维护者**: 团队  
**最后更新**: 2026-02-26
