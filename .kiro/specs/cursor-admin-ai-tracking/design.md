# Design: AI Code Tracking API 集成

> **目标**：AI Code Tracking API 的客户端实现、同步逻辑、数据模型与查询 API 的技术设计。  
> **状态**：待实施  
> **最后更新**：2026-02-28

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-ai-tracking/requirements.md`
- design: `.kiro/specs/cursor-admin-ai-tracking/design.md`
- tasks: `.kiro/specs/cursor-admin-ai-tracking/tasks.md`

---

## 1. 架构

```
Cursor AI Code Tracking API
    │
    │  GET /analytics/ai-code/commits
    │  (startDate, endDate, page, pageSize)
    │
    ▼
cursor_api.py :: get_ai_code_commits()
    │  分页遍历 + ETag 缓存 + 退避重试
    │
    ▼
ai_code_sync.py :: sync_ai_code_commits()
    │  增量同步（上次同步时间 → now）
    │  幂等 upsert → ai_code_commits 表
    │  自动匹配 project_id
    │
    ▼
main.py :: APScheduler 定时任务（每小时）
```

---

## 2. cursor_api.py 扩展

```python
async def get_ai_code_commits(
    start_date: str,
    end_date: str,
    page: int = 1,
    page_size: int = 1000,
    user: str | None = None,
) -> dict:
    """
    GET /analytics/ai-code/commits
    Returns: {"commits": [...], "pagination": {"page", "pageSize", "totalCount"}}
    """
```

- 使用 Basic Auth（API Key 作为 username，密码为空）。
- 支持 `If-None-Match` header（ETag 缓存）。
- Rate limit 20 req/min，收到 429 时指数退避（1s, 2s, 4s...）。

### 响应字段映射

| API 字段 | 表字段 |
|----------|--------|
| `commitHash` | `commit_hash` |
| `userId` | `user_id` |
| `userEmail` | `user_email` |
| `repoName` | `repo_name` |
| `branchName` | `branch_name` |
| `totalLinesAdded` | `total_lines_added` |
| `totalLinesDeleted` | `total_lines_deleted` |
| `tabLinesAdded` | `tab_lines_added` |
| `tabLinesDeleted` | `tab_lines_deleted` |
| `composerLinesAdded` | `composer_lines_added` |
| `composerLinesDeleted` | `composer_lines_deleted` |
| `nonAiLinesAdded` | `non_ai_lines_added` |
| `nonAiLinesDeleted` | `non_ai_lines_deleted` |
| `message` | `commit_message` |
| `commitTs` | `commit_ts` |

---

## 3. ai_code_sync.py

```python
async def sync_ai_code_commits():
    """
    1. 查询 ai_code_commits 表最大 commit_ts 作为 start_date（首次用 30d）
    2. 分页拉取 start_date → now 的所有 commit
    3. 对每个 commit：
       a. 匹配 project_id（repo_name → projects.git_repos）
       b. upsert 到 ai_code_commits（ON CONFLICT (commit_hash, user_email) DO UPDATE）
    4. 记录同步结果日志
    """
```

### project_id 匹配逻辑

```python
def match_project(repo_name: str, projects: list[dict]) -> int | None:
    """
    repo_name 格式通常为 "org/repo-name"
    projects.git_repos 可能为:
      - "https://gitlab.com/org/repo-name.git"
      - "git@gitlab.com:org/repo-name.git"
      - "org/repo-name"
    从 git_repos 中提取 "org/repo-name" 部分进行匹配。
    """
```

---

## 4. 查询 API

### 4.1 管理端

```
GET /api/ai-commits?project_id=1&user_email=alice@co.com&start=2026-02-01&end=2026-02-28&page=1&page_size=50
```

Response:
```json
{
  "items": [
    {
      "commit_hash": "abc123",
      "user_email": "alice@co.com",
      "repo_name": "org/project-a",
      "project_name": "Project A",
      "ai_lines_added": 120,
      "total_lines_added": 150,
      "ai_ratio": 0.8,
      "commit_ts": "2026-02-28T10:00:00Z"
    }
  ],
  "total": 42,
  "page": 1
}
```

### 4.2 汇总

```
GET /api/ai-commits/summary?project_id=1&period=monthly&period_key=2026-02
```

Response:
```json
{
  "project_id": 1,
  "project_name": "Project A",
  "period": "2026-02",
  "members": [
    {
      "user_email": "alice@co.com",
      "ai_lines_added": 1200,
      "total_lines_added": 1500,
      "ai_ratio": 0.8,
      "commit_count": 15
    }
  ],
  "totals": {
    "ai_lines_added": 3500,
    "total_lines_added": 4000,
    "ai_ratio": 0.875,
    "commit_count": 42
  }
}
```

### 4.3 成员端

```
GET /api/ai-commits/my?period=monthly&period_key=2026-02
```

Response:
```json
{
  "user_email": "alice@co.com",
  "period": "2026-02",
  "total_ai_lines": 1200,
  "total_lines": 1500,
  "ai_ratio": 0.8,
  "projects": [
    {"project_id": 1, "project_name": "Project A", "ai_lines": 800},
    {"project_id": 2, "project_name": "Project B", "ai_lines": 400}
  ],
  "trend": [
    {"week": "2026-W05", "ai_lines": 250},
    {"week": "2026-W06", "ai_lines": 300}
  ]
}
```

---

## 5. 迁移

新增 `004_ai_code_commits.sql`（幂等）：
- CREATE TABLE `ai_code_commits`
- CREATE INDEX

---

## 6. 定时任务注册

在 `main.py` 的 APScheduler 中注册：

```python
scheduler.add_job(sync_ai_code_commits, "interval", hours=1, id="ai_code_sync")
```

在现有 `sync_all` 之后执行，或独立调度。

---

**维护者**: 团队  
**最后更新**: 2026-02-28
