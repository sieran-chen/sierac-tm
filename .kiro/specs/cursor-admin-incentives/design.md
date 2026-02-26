# Design: 贡献可视化与团队激励

> **目标**：基于 projects、git_contributions、agent_sessions、daily_usage 四张表，实现贡献度计算、个人贡献画像、排行榜与激励闭环的技术设计。  
> **状态**：预留设计（待 cursor-admin-projects 完成后启动实施）  
> **最后更新**：2026-02-26

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-incentives/requirements.md`
- design: `.kiro/specs/cursor-admin-incentives/design.md`
- tasks: `.kiro/specs/cursor-admin-incentives/tasks.md`

---

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│  数据来源（已有表）                                               │
│  git_contributions  → 代码产出（第一数据源）                      │
│  agent_sessions     → 项目参与（Hook 信号，仅装 Hook 者有）        │
│  daily_usage        → AI 使用量（效率参考，全员有）               │
└────────────────────────────┬────────────────────────────────────┘
                             │ 定时计算任务（每日/每周）
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  contribution_engine.py（贡献度计算引擎）                         │
│  ├── 读取 incentive_rules（权重配置）                             │
│  ├── 按 project_id + user_email + 周期 聚合各维度得分             │
│  └── 写入 contribution_scores + leaderboard_snapshots            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Collector API（新增路由）                                        │
│  GET /api/contributions/my          → 成员端：我的贡献            │
│  GET /api/contributions/leaderboard → 管理端：排行榜              │
│  GET /api/incentive-rules           → 管理端：规则配置            │
│  PUT /api/incentive-rules/{id}      → 管理端：修改规则            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据模型

### 2.1 incentive_rules 表

```sql
CREATE TABLE IF NOT EXISTS incentive_rules (
    id              SERIAL PRIMARY KEY,
    name            TEXT        NOT NULL,           -- 规则名称（如「默认规则」）
    period_type     TEXT        NOT NULL DEFAULT 'weekly',  -- daily / weekly / monthly
    weights         JSONB       NOT NULL,           -- 各维度权重，见下方
    caps            JSONB       NOT NULL DEFAULT '{}', -- 各维度上限
    enabled         BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

`weights` 示例：

```json
{
  "lines_added": 0.35,
  "commit_count": 0.20,
  "session_duration_hours": 0.25,
  "agent_requests": 0.10,
  "files_changed": 0.10
}
```

`caps` 示例（防刷上限）：

```json
{
  "session_duration_hours_per_day": 12,
  "agent_requests_per_day": 500
}
```

### 2.2 contribution_scores 表

```sql
CREATE TABLE IF NOT EXISTS contribution_scores (
    id              SERIAL PRIMARY KEY,
    user_email      TEXT        NOT NULL,
    project_id      INT         REFERENCES projects(id),  -- NULL = 跨项目汇总
    period_type     TEXT        NOT NULL,                  -- weekly / monthly
    period_key      TEXT        NOT NULL,                  -- 如 "2026-W08" / "2026-02"
    rule_id         INT         REFERENCES incentive_rules(id),
    -- 原始维度数据
    lines_added     INT         NOT NULL DEFAULT 0,
    lines_removed   INT         NOT NULL DEFAULT 0,
    commit_count    INT         NOT NULL DEFAULT 0,
    files_changed   INT         NOT NULL DEFAULT 0,
    session_duration_hours NUMERIC(8,2) NOT NULL DEFAULT 0,
    agent_requests  INT         NOT NULL DEFAULT 0,
    -- 计算得分
    score_breakdown JSONB       NOT NULL DEFAULT '{}',  -- 各维度得分明细
    total_score     NUMERIC(10,2) NOT NULL DEFAULT 0,
    rank            INT,                                -- 本周期排名（NULL=未参与排行）
    hook_adopted    BOOLEAN     NOT NULL DEFAULT FALSE, -- 本周期是否有 Hook 数据
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_email, project_id, period_type, period_key)
);

CREATE INDEX IF NOT EXISTS idx_scores_period ON contribution_scores (period_type, period_key, total_score DESC);
CREATE INDEX IF NOT EXISTS idx_scores_user   ON contribution_scores (user_email, period_type, period_key);
```

### 2.3 leaderboard_snapshots 表（可选，审计用）

```sql
CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
    id          SERIAL PRIMARY KEY,
    period_type TEXT        NOT NULL,
    period_key  TEXT        NOT NULL,
    snapshot    JSONB       NOT NULL,  -- 完整排行数据快照
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (period_type, period_key)
);
```

---

## 3. 贡献度计算引擎

### 3.1 计算流程

```python
# contribution_engine.py

def calculate_period(period_type: str, period_key: str, rule: IncentiveRule):
    # 1. 从 git_contributions 聚合代码产出（按 user_email + project_id）
    git_data = aggregate_git(period_type, period_key)

    # 2. 从 agent_sessions 聚合参与数据（按 user_email + project_id）
    session_data = aggregate_sessions(period_type, period_key)

    # 3. 从 daily_usage 聚合 AI 用量（按 user_email）
    usage_data = aggregate_usage(period_type, period_key)

    # 4. 合并三源数据，按 user_email + project_id 计算得分
    for (user_email, project_id), data in merge(git_data, session_data, usage_data):
        score_breakdown = {}
        total = 0
        for dim, weight in rule.weights.items():
            raw = min(data.get(dim, 0), rule.caps.get(f"{dim}_cap", float("inf")))
            score_breakdown[dim] = raw * weight
            total += score_breakdown[dim]

        hook_adopted = (user_email, project_id) in session_data

        upsert contribution_scores(
            user_email, project_id, period_type, period_key,
            rule_id=rule.id,
            score_breakdown=score_breakdown,
            total_score=total,
            hook_adopted=hook_adopted,
            ...raw dimensions...
        )

    # 5. 计算排名（仅 hook_adopted=True 的成员参与排行）
    update_ranks(period_type, period_key)

    # 6. 保存排行快照
    save_leaderboard_snapshot(period_type, period_key)
```

### 3.2 触发时机

- 每日 00:30（UTC+8）：计算前一天的 daily 得分。
- 每周一 01:00：计算上一周的 weekly 得分。
- 每月 1 日 01:30：计算上一月的 monthly 得分。
- 管理员可在管理端手动触发重新计算。

### 3.3 数据缺失处理

| 场景 | 处理 |
|------|------|
| 成员无 Hook 数据（未装 Hook） | `hook_adopted=false`；session 维度得分为 0；不参与排行 |
| 成员无 Git 数据（无 commit） | git 维度得分为 0；仍可参与排行（若有 Hook 数据） |
| 成员无 daily_usage 数据 | usage 维度得分为 0 |
| 三源均无数据 | 不写入 contribution_scores |

---

## 4. API 设计

### 4.1 成员端

```
GET /api/contributions/my?period_type=weekly&period_key=2026-W08&project_id=1
```

Response：

```json
{
  "user_email": "alice@company.com",
  "period_type": "weekly",
  "period_key": "2026-W08",
  "hook_adopted": true,
  "total_score": 87.5,
  "rank": 3,
  "score_breakdown": {
    "lines_added": 35.0,
    "commit_count": 18.0,
    "session_duration_hours": 21.25,
    "agent_requests": 8.75,
    "files_changed": 4.5
  },
  "raw": {
    "lines_added": 1200,
    "commit_count": 9,
    "session_duration_hours": 8.5,
    "agent_requests": 87,
    "files_changed": 45
  },
  "projects": [
    {"project_id": 1, "project_name": "Sierac-tm", "total_score": 60.0},
    {"project_id": 2, "project_name": "OwlClaw", "total_score": 27.5}
  ]
}
```

### 4.2 管理端排行榜

```
GET /api/contributions/leaderboard?period_type=weekly&period_key=2026-W08&hook_only=true
```

Response：

```json
{
  "period_type": "weekly",
  "period_key": "2026-W08",
  "generated_at": "2026-02-25T01:00:00Z",
  "entries": [
    {
      "rank": 1,
      "user_email": "bob@company.com",
      "total_score": 95.2,
      "hook_adopted": true,
      "lines_added": 1800,
      "commit_count": 12
    }
  ]
}
```

- `hook_only=true`（默认）：仅返回 `hook_adopted=true` 的成员。
- `hook_only=false`：返回所有成员，未接入 Hook 者标注 `hook_adopted=false`，session 维度为 0。

### 4.3 规则管理

```
GET  /api/incentive-rules          → 列表
POST /api/incentive-rules          → 新建
PUT  /api/incentive-rules/{id}     → 修改权重/周期/上限
DELETE /api/incentive-rules/{id}   → 停用（软删除）
POST /api/incentive-rules/{id}/recalculate  → 手动触发重新计算
```

---

## 5. 管理端页面

### 5.1 排行榜页

- 周期选择器（周/月）+ 时间范围。
- 排行表：排名、成员、总分、各维度得分、Hook 状态。
- 支持「仅已接入 Hook」过滤。
- 可导出 CSV。

### 5.2 我的贡献页（成员端）

- 本周期得分卡（总分、排名、各维度）。
- 历史趋势折线图（近 8 周/月）。
- 项目维度分布（按项目展示贡献占比）。
- Hook 状态提示（未接入时引导安装）。

### 5.3 规则配置页（管理端）

- 当前启用规则的权重可视化（饼图或条形图）。
- 权重滑块编辑（总和自动归一化到 100%）。
- 上限配置表单。
- 「重新计算」按钮（触发当前周期重算）。

---

## 6. 与其他模块的边界

| 模块 | 交互 |
|------|------|
| cursor-admin-core | 读取 daily_usage、agent_sessions；共享 DB 连接池 |
| cursor-admin-projects | 读取 projects、git_contributions；按 project_id 聚合 |
| cursor-admin-hooks | 不直接交互；Hook 数据已落入 agent_sessions |

激励模块**不修改**任何已有表；仅新增 `incentive_rules`、`contribution_scores`、`leaderboard_snapshots` 三张表，以及对应的计算任务与 API。

---

## 7. 迁移策略

- 新增 `003_incentives.sql` 迁移文件（幂等）。
- 首次计算时，历史数据（project_id=NULL 的 agent_sessions）不参与排行，但 git_contributions 和 daily_usage 可回溯计算。
- 默认规则（`incentive_rules` 初始数据）在迁移文件中 INSERT（ON CONFLICT DO NOTHING）。

---

## 8. 参考文档

- `docs/ARCHITECTURE.md` §5（扩展：团队激励管理）
- `.kiro/specs/cursor-admin-core/design.md`（agent_sessions、daily_usage 表结构）
- `.kiro/specs/cursor-admin-projects/design.md`（git_contributions、projects 表结构）
- `.kiro/specs/cursor-admin-incentives/requirements.md`（§4 与 Hook 挂钩设计）

---

**维护者**: 团队  
**最后更新**: 2026-02-26  
**状态**: 预留设计（待 cursor-admin-projects 完成后启动）
