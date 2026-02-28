# Sierac-tm 总体架构

> **版本**: v3.0.0  
> **状态**: 架构真源  
> **最后更新**: 2026-02-28  
> **适用范围**: 文档驱动开发、Spec 设计、集成边界

---

## 一、项目定位

**Sierac-tm** 是一个**基于 Cursor 官方数据的项目激励平台**。

> **核心理念：立项定预算，数据看贡献，激励促转型。**

平台帮助团队管理者：
1. **立项**：登记公司项目，关联仓库，设定预算与激励池。
2. **看贡献**：基于 Cursor 官方 API 自动采集 AI 代码贡献、用量、支出，按项目和成员可视化。
3. **做激励**：根据贡献数据自动计算激励分配，推动团队向 AI 驱动研发转型。

### 设计原则

| 原则 | 说明 |
|------|------|
| **纯服务端** | 不在成员机器上安装任何东西（无 Hook、无客户端），零部署成本 |
| **官方数据驱动** | 所有数据来自 Cursor 官方 API，无法绕开、无法作假 |
| **激励而非监控** | 展示贡献、激励参与，不做拦截、不做负面排名 |
| **简单规则** | 激励规则透明、简单，每个人不用计算器就能算出自己的份额 |
| **轻量立项** | 立项 = 登记项目信息，不自动创建仓库、不注入 Hook |

---

## 二、系统边界

```
                    ┌─────────────────────────────────────────┐
                    │         Cursor Platform                  │
                    │  Admin API / Analytics API /             │
                    │  AI Code Tracking API                    │
                    └──────────────────┬──────────────────────┘
                                       │ HTTPS, API Key
                                       ▼
                              ┌─────────────────────────────┐
                              │  Sierac-tm (本系统)           │
                              │  collector (FastAPI)          │
                              │    ├─ 项目立项（预算+激励池） │
                              │    ├─ Cursor API 数据同步     │
                              │    ├─ AI 代码贡献同步         │
                              │    ├─ 贡献度计算 & 激励分配   │
                              │    ├─ 告警检测与通知          │
                              │    └─ 管理端 & 成员端 API     │
                              │  db (PostgreSQL)              │
                              │  web (React + Nginx)          │
                              └─────────────────────────────┘
```

- **入**：Cursor Admin API（成员/用量/支出）、Cursor Analytics API（团队趋势）、Cursor AI Code Tracking API（commit 级 AI 代码归因）。
- **出**：管理端展示、成员端「我的贡献」、邮件/Webhook 告警、激励报告。

---

## 三、数据来源（Cursor 官方 API）

| API | 采集频率 | 落库表 | 提供的数据 |
|-----|----------|--------|-----------|
| **Admin API** `/teams/members` | 每日 | `members` | 成员列表 |
| **Admin API** `/teams/daily-usage-data` | 每小时 | `daily_usage` | 每日用量（请求数、Token、模型分布） |
| **Admin API** `/teams/user-spend` | 每小时 | `spend_snapshots` | 按人支出 |
| **AI Code Tracking API** `/analytics/ai-code/commits` | 每小时 | `ai_code_commits` | 每个 commit 的 AI 代码归因（TAB/Composer/手写） |

**关键决策**：
- **AI Code Tracking API 是贡献的第一数据源**：它直接给出「谁在哪个仓库的哪个 commit 用 AI 写了多少行代码」，这是最客观、最难作假的度量。
- **Admin API 是效率和成本参考**：用量和支出数据用于预算追踪和效率分析。
- **所有 Cursor API 调用必须经 `cursor_api.py`**，不得在其他模块直接请求。

---

## 四、包结构

```
Sierac-tm/
├── cursor-admin/              # 主应用
│   ├── collector/             # 采集服务（Python, FastAPI）
│   │   ├── main.py            # 入口、API、定时任务
│   │   ├── sync.py            # Cursor Admin/Analytics API 同步
│   │   ├── ai_code_sync.py   # AI Code Tracking API 同步
│   │   ├── contribution_engine.py  # 贡献度计算与激励分配
│   │   ├── alerts.py          # 告警检测与通知
│   │   ├── cursor_api.py      # Cursor API 客户端（唯一出口）
│   │   ├── database.py        # 连接与迁移
│   │   └── config.py
│   ├── db/
│   │   └── migrations/        # SQL 迁移（幂等）
│   └── web/                   # 管理端 + 成员端（TypeScript, React, Vite）
│       └── src/
│           └── pages/
│               ├── ProjectsPage.tsx        # 项目管理
│               ├── ProjectDetailPage.tsx   # 项目详情（预算+贡献）
│               ├── MyContributionsPage.tsx  # 我的贡献
│               ├── LeaderboardPage.tsx     # 排行榜
│               └── IncentiveRulesPage.tsx  # 激励规则配置
├── docs/                      # 架构与产品文档
├── .kiro/                     # Spec 文档（文档驱动）
│   └── specs/
├── .cursor/rules/             # Cursor 规则
└── docker-compose.yml
```

| 层次 | 技术选型 | 说明 |
|------|----------|------|
| 采集服务 | Python 3.12, FastAPI, asyncpg, APScheduler | 数据同步、计算、API |
| 管理端 | TypeScript, React, Vite, Tailwind, Recharts | 看板与配置 UI |
| 数据库 | PostgreSQL 16 | 持久化；SQL 文件幂等迁移 |
| 部署 | Docker Compose | db + collector + web |

---

## 五、核心数据流

```
管理员立项 → POST /api/projects → projects 表
    │                                  （名称、仓库、成员、预算、激励池）
    │
    ▼
Cursor AI Code Tracking API → ai_code_sync.py 定时拉取
    │                          → ai_code_commits 表
    │                          （commit hash、user、repo、AI行数/手写行数）
    │                          → 通过 repo_name 匹配 projects.git_repos 自动归属
    │
Cursor Admin API → sync.py 定时拉取
    │               → members, daily_usage, spend_snapshots
    │
    ▼
贡献度计算 → contribution_engine.py
    │         → 按项目+成员+周期聚合 AI 代码贡献
    │         → 结合激励规则计算得分与激励分配
    │         → contribution_scores + leaderboard_snapshots
    │
    ▼
管理端：项目维度（预算消耗+贡献）、人员维度（排行+激励）
成员端：我的贡献（AI 代码、效率趋势、激励份额）
```

---

## 六、核心实体：项目（Project）

**项目是平台的一等实体**。所有贡献数据、预算、激励都围绕「项目」组织。

### 6.1 立项 = 登记

```
管理员在平台「立项」
    → 填写项目信息（名称、描述、关联仓库地址、参与成员）
    → 设定预算（本周期 Token 预算额度）
    → 设定激励池（本项目的激励金额或比例）
    → 系统自动通过 AI Code Tracking API 匹配 repo_name 归属数据
```

立项不创建仓库、不注入 Hook、不做白名单。就是一个登记动作。

### 6.2 项目数据模型

| 字段 | 说明 |
|------|------|
| `id` | 项目 ID |
| `name` | 项目名称 |
| `description` | 项目描述 |
| `git_repos` | 关联的 Git 仓库地址（可多个，用于匹配 AI Code Tracking 数据） |
| `member_emails` | 参与成员（可选，不填则全员可用） |
| `status` | 状态（active / archived） |
| `budget_amount` | 预算额度（本周期） |
| `budget_period` | 预算周期（monthly / quarterly） |
| `incentive_pool` | 激励池金额 |
| `incentive_rule_id` | 关联的激励规则 |
| `created_by` | 立项人 |
| `created_at` / `updated_at` | 时间戳 |

### 6.3 数据归属

AI Code Tracking API 返回每个 commit 的 `repoName`，系统通过匹配 `projects.git_repos` 自动将 commit 归属到项目。无需 Hook、无需白名单、无需工作目录匹配。

---

## 七、AI 代码贡献（核心数据表）

```sql
-- AI Code Tracking API 同步的 commit 级数据
ai_code_commits (
    commit_hash, user_email, repo_name, branch_name,
    project_id,              -- 通过 repo_name 匹配 projects.git_repos
    total_lines_added, total_lines_deleted,
    tab_lines_added, tab_lines_deleted,         -- TAB 补全
    composer_lines_added, composer_lines_deleted, -- Composer 生成
    non_ai_lines_added, non_ai_lines_deleted,   -- 手写
    commit_message, commit_ts, synced_at
)
```

这张表回答所有核心问题：
- **谁**（user_email）在**哪个项目**（project_id）**什么时候**（commit_ts）用 **AI 写了多少代码**（tab + composer lines）
- AI 代码占比 = (tab + composer) / total
- 按人按项目按周期聚合 → 贡献度 → 激励分配

---

## 八、激励模块

### 8.1 设计原则

- **简单**：3-5 个核心指标，规则透明
- **自动**：数据全部来自 API，零人工录入
- **公平**：官方数据无法作假，按贡献分配

### 8.2 激励计算

```
项目激励池 × 成员在该项目的 AI 代码贡献占比 × 交付系数
```

- **AI 代码贡献占比**：成员的 AI 代码行数 / 项目全部 AI 代码行数
- **交付系数**：按时交付 1.0，延期递减（管理员手动设定）
- 每个周期（月/季度）自动生成激励快照

### 8.3 核心表

- `incentive_rules`：激励规则（周期、权重配置）
- `contribution_scores`：按人按项目按周期的贡献得分
- `leaderboard_snapshots`：排行快照（审计用）

---

## 九、已废弃的能力

以下能力在 v3.0 中**正式废弃**，不再维护：

| 废弃项 | 原因 | 替代方案 |
|--------|------|----------|
| **Cursor Hook**（Python + Java） | 可被绕开、部署成本高、官方 API 数据更全 | AI Code Tracking API |
| **白名单准入拦截** | 过度工程，管理手段即可解决 | 项目立项 + 数据透明 |
| **GitLab 仓库自动创建** | 过度工程 | 手动关联仓库地址 |
| **Hook 模板注入** | 随 Hook 废弃 | 无需 |
| **agent_sessions 表** | 数据来源（Hook）已废弃 | ai_code_commits |
| **git_sync.py**（Git CLI 扫描） | AI Code Tracking API 提供更精确的数据 | ai_code_sync.py |
| **gitlab_client.py** | 不再需要 GitLab API 集成 | 无需 |
| **闭环健康/Hook 状态检测** | Hook 已废弃 | 无需 |

---

## 十、集成边界

| 能力 | 自建 | 集成 | 隔离位置 |
|------|------|------|----------|
| 项目立项、贡献聚合、激励计算 | ✅ | | collector/*.py |
| Cursor API 调用 | | ✅ Cursor 官方 | **cursor_api.py 唯一** |
| 管理端 + 成员端 | ✅ | | web/src |
| 数据库 | ✅ | PostgreSQL | db/migrations |

**约束**：
- 所有 Cursor API 调用必须经 `cursor_api.py`，不得在其他模块直接请求。
- API 层做可插拔适配器模式，便于未来接入其他数据源。

---

## 十一、数据库

- **PostgreSQL 16**，迁移为 SQL 文件幂等执行。
- 时间字段统一 **TIMESTAMPTZ**。
- 核心表：`projects`、`members`、`daily_usage`、`spend_snapshots`、`ai_code_commits`、`contribution_scores`、`incentive_rules`、`leaderboard_snapshots`、`alert_rules`、`alert_events`。

---

## 十二、文档引用

| 查什么 | 去哪里 |
|--------|--------|
| 架构决策 | 本文档 `docs/ARCHITECTURE.md` |
| Spec 总览 | `.kiro/specs/SPEC_TASKS_SCAN.md` |
| 项目立项设计 | `.kiro/specs/cursor-admin-projects/` |
| AI 代码同步设计 | `.kiro/specs/cursor-admin-ai-tracking/` |
| 激励设计 | `.kiro/specs/cursor-admin-incentives/` |
| Cursor API 配置 | `docs/CURSOR-API-SETUP.md` |

---

**维护者**: yeemio  
**最后更新**: 2026-02-28
