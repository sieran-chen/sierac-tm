# Design: 项目立项

> **目标**：轻量立项的数据模型、API 设计与前端页面。  
> **状态**：待重构（v3.0 简化）  
> **最后更新**：2026-02-28

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-projects/requirements.md`
- design: `.kiro/specs/cursor-admin-projects/design.md`
- tasks: `.kiro/specs/cursor-admin-projects/tasks.md`

---

## 1. 数据模型

### projects 表（v3.0 简化）

```sql
CREATE TABLE IF NOT EXISTS projects (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    git_repos       TEXT[] NOT NULL DEFAULT '{}',
    member_emails   TEXT[] NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'active',
    budget_amount   NUMERIC(12,2),
    budget_period   TEXT DEFAULT 'monthly',
    incentive_pool  NUMERIC(12,2),
    incentive_rule_id INT REFERENCES incentive_rules(id),
    created_by      TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

**v3.0 移除的字段**（相比 v2）：
- `workspace_rules` — 不再需要白名单匹配
- `gitlab_project_id` / `repo_url` / `repo_ssh_url` — 不再自动创建仓库
- `hook_initialized` — 不再注入 Hook

**v3.0 新增的字段**：
- `budget_amount` — 预算额度
- `budget_period` — 预算周期（monthly / quarterly）
- `incentive_pool` — 激励池金额
- `incentive_rule_id` — 关联的激励规则

---

## 2. API 设计

### 2.1 项目 CRUD

```
GET    /api/projects              → 项目列表（支持 status 筛选）
POST   /api/projects              → 新建项目
GET    /api/projects/{id}         → 项目详情
PUT    /api/projects/{id}         → 编辑项目
DELETE /api/projects/{id}         → 归档（status → archived）
```

### 2.2 项目汇总

```
GET /api/projects/{id}/summary
```

Response:
```json
{
  "project": {"id": 1, "name": "Sierac-tm", "status": "active"},
  "budget": {
    "amount": 10000,
    "period": "monthly",
    "spent_estimate": 3500
  },
  "contribution": {
    "total_ai_lines": 15413,
    "total_lines": 17793,
    "ai_ratio": 0.874,
    "commit_count": 120,
    "member_count": 5
  },
  "incentive_pool": 5000
}
```

`spent_estimate` 通过 `spend_snapshots` 按 `member_emails` 聚合估算。

### 2.3 项目成员贡献

```
GET /api/projects/{id}/members?start=2026-02-01&end=2026-02-28
```

Response:
```json
{
  "members": [
    {
      "user_email": "alice@co.com",
      "ai_lines_added": 5000,
      "total_lines_added": 6000,
      "ai_ratio": 0.833,
      "commit_count": 40,
      "contribution_pct": 0.35
    }
  ]
}
```

---

## 3. 数据归属逻辑

AI Code Tracking API 返回 `repoName`（格式如 `sieran-chen/sierac-tm`）。

匹配逻辑（在 `ai_code_sync.py` 中）：
1. 从 `projects.git_repos` 提取标准化名称（去掉协议、域名、`.git` 后缀）。
2. 与 commit 的 `repoName` 做大小写不敏感匹配。
3. 匹配成功写入 `project_id`；未匹配的 commit `project_id` 为 NULL。

---

## 4. 前端页面

### 4.1 项目列表页（ProjectsPage）

- 项目卡片：名称、状态标签、预算/已用、AI 代码总量、成员数。
- 操作：新建、编辑、归档。
- 筛选：active / archived / all。

### 4.2 项目详情页（ProjectDetailPage）

- 基本信息：名称、描述、关联仓库、成员。
- 预算卡片：预算额度、估算支出、剩余。
- 贡献卡片：AI 代码总量、AI 占比、commit 数。
- 成员贡献表：按 AI 代码贡献排序。
- 激励池信息：金额、分配预览。

---

## 5. 迁移策略

- 新增迁移 `005_projects_v3.sql`：
  - ALTER TABLE projects ADD COLUMN budget_amount, budget_period, incentive_pool, incentive_rule_id（IF NOT EXISTS）。
  - 不删除旧字段（兼容），但代码中不再使用 workspace_rules、gitlab_project_id 等。

---

**维护者**: 团队  
**最后更新**: 2026-02-28
