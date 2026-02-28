# Design: 项目激励

> **目标**：基于 ai_code_commits 的简单激励计算、排行榜与成员端展示。  
> **状态**：待重构（v3.0 简化）  
> **最后更新**：2026-02-28

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-incentives/requirements.md`
- design: `.kiro/specs/cursor-admin-incentives/design.md`
- tasks: `.kiro/specs/cursor-admin-incentives/tasks.md`

---

## 1. 架构

```
ai_code_commits 表（按 project_id + user_email + 周期聚合）
    ↓
contribution_engine.py
    ├── 读取 incentive_rules（周期配置）
    ├── 读取 projects（激励池、交付系数）
    ├── 聚合 AI 代码贡献 → 计算占比
    ├── 激励池 × 占比 × 交付系数 → 激励金额
    └── 写入 contribution_scores + leaderboard_snapshots
    ↓
API 路由
    ├── GET /api/contributions/my          → 成员端
    ├── GET /api/contributions/leaderboard → 管理端
    └── GET /api/incentive-rules           → 规则管理
```

---

## 2. 数据模型

### 2.1 incentive_rules 表（简化）

```sql
CREATE TABLE IF NOT EXISTS incentive_rules (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    period_type     TEXT NOT NULL DEFAULT 'monthly',
    description     TEXT DEFAULT '',
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

规则本身很简单：只定义周期。核心公式固定为 `激励池 × 贡献占比 × 交付系数`。

### 2.2 contribution_scores 表（简化）

```sql
CREATE TABLE IF NOT EXISTS contribution_scores (
    id              SERIAL PRIMARY KEY,
    user_email      TEXT NOT NULL,
    project_id      INT REFERENCES projects(id),
    period_type     TEXT NOT NULL,
    period_key      TEXT NOT NULL,
    rule_id         INT REFERENCES incentive_rules(id),
    ai_lines_added  INT NOT NULL DEFAULT 0,
    total_lines_added INT NOT NULL DEFAULT 0,
    commit_count    INT NOT NULL DEFAULT 0,
    ai_ratio        NUMERIC(5,4) NOT NULL DEFAULT 0,
    contribution_pct NUMERIC(5,4) NOT NULL DEFAULT 0,
    delivery_factor NUMERIC(3,2) NOT NULL DEFAULT 1.0,
    incentive_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    rank            INT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_email, project_id, period_type, period_key)
);
```

### 2.3 leaderboard_snapshots 表

```sql
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
    id          SERIAL PRIMARY KEY,
    period_type TEXT NOT NULL,
    period_key  TEXT NOT NULL,
    snapshot    JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (period_type, period_key)
);
```

---

## 3. 计算引擎

```python
async def calculate_period(period_type: str, period_key: str):
    # 1. 从 ai_code_commits 聚合（按 project_id + user_email）
    #    SUM(tab_lines_added + composer_lines_added) as ai_lines
    #    SUM(total_lines_added) as total_lines
    #    COUNT(DISTINCT commit_hash) as commits

    # 2. 对每个 project：
    #    project_total_ai = SUM(所有成员的 ai_lines)
    #    contribution_pct = member_ai_lines / project_total_ai

    # 3. 读取 project.incentive_pool 和 delivery_factor
    #    incentive_amount = incentive_pool * contribution_pct * delivery_factor

    # 4. upsert contribution_scores

    # 5. 计算排名（按 ai_lines_added DESC）

    # 6. 保存 leaderboard_snapshot
```

### 触发时机

- 每周一 01:00（Asia/Shanghai）：计算上一周。
- 每月 1 日 01:30：计算上一月。
- 管理员可手动触发重新计算。

---

## 4. API 设计

### 4.1 成员端

```
GET /api/contributions/my?period_type=monthly&period_key=2026-02
```

Response:
```json
{
  "user_email": "alice@co.com",
  "period_type": "monthly",
  "period_key": "2026-02",
  "total_ai_lines": 5000,
  "total_lines": 6000,
  "ai_ratio": 0.833,
  "rank": 2,
  "total_incentive": 2500,
  "projects": [
    {
      "project_id": 1,
      "project_name": "Sierac-tm",
      "ai_lines": 3000,
      "contribution_pct": 0.35,
      "incentive_amount": 1750
    }
  ],
  "trend": [
    {"period_key": "2026-01", "ai_lines": 4200, "incentive": 2100},
    {"period_key": "2026-02", "ai_lines": 5000, "incentive": 2500}
  ]
}
```

### 4.2 排行榜

```
GET /api/contributions/leaderboard?period_type=monthly&period_key=2026-02
```

Response:
```json
{
  "period_type": "monthly",
  "period_key": "2026-02",
  "entries": [
    {
      "rank": 1,
      "user_email": "bob@co.com",
      "ai_lines_added": 8000,
      "ai_ratio": 0.9,
      "total_incentive": 4000
    }
  ]
}
```

### 4.3 规则管理

```
GET    /api/incentive-rules
POST   /api/incentive-rules
PUT    /api/incentive-rules/{id}
POST   /api/incentive-rules/{id}/recalculate
```

---

## 5. 前端页面

### 5.1 排行榜页（LeaderboardPage）

- 周期选择器（月/周）。
- 排行表：排名、成员、AI 代码行数、AI 占比、激励金额。
- 导出 CSV。

### 5.2 我的贡献页（MyContributionsPage）

- 本周期得分卡：AI 代码行数、排名、激励金额。
- 历史趋势折线图。
- 项目维度分布饼图。

### 5.3 激励规则页（IncentiveRulesPage）

- 当前规则展示。
- 交付系数编辑（按项目）。
- 「重新计算」按钮。

---

## 6. 迁移

- 更新 `003_incentives.sql`（或新增 `006_incentives_v3.sql`）：
  - 简化 `contribution_scores` 表结构
  - 简化 `incentive_rules` 表结构
  - 新增 `incentive_amount`、`delivery_factor` 等字段

---

**维护者**: 团队  
**最后更新**: 2026-02-28
