# Requirements: AI Code Tracking API 集成

> **目标**：集成 Cursor AI Code Tracking API，实现 commit 级 AI 代码归因数据的自动采集与落库，作为贡献度量的核心数据源。  
> **优先级**：P0（贡献可视化与激励的数据基础）  
> **预估工作量**：3–5 天

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-ai-tracking/requirements.md`
- design: `.kiro/specs/cursor-admin-ai-tracking/design.md`
- tasks: `.kiro/specs/cursor-admin-ai-tracking/tasks.md`

---

## 1. 背景与动机

- Cursor 官方 AI Code Tracking API 提供 commit 级别的 AI 代码归因数据，精确区分 TAB 补全、Composer 生成、手写代码的行数。
- 该数据是贡献度量的最佳来源：基于实际 commit，无法绕开，无需客户端部署。
- 替代原有的 `git_sync.py`（Git CLI 扫描）和 `agent_sessions`（Hook 上报），提供更精确、更可靠的数据。

---

## 2. 用户故事

### 2.1 作为管理员

**故事**：系统自动从 Cursor AI Code Tracking API 采集团队成员的 AI 代码贡献数据，按项目和成员展示。

**验收标准**：
- [ ] 系统定时（每小时）从 AI Code Tracking API 拉取 commit 数据并落库。
- [ ] 每个 commit 记录：用户、仓库、分支、AI 行数（TAB + Composer）、手写行数、时间。
- [ ] commit 数据通过 `repoName` 自动匹配已立项项目的 `git_repos`，写入 `project_id`。
- [ ] 管理端可按项目、成员、时间范围查看 AI 代码贡献。

### 2.2 作为成员

**故事**：我能看到自己在各项目的 AI 代码贡献明细和趋势。

**验收标准**：
- [ ] 成员端「我的贡献」展示我的 AI 代码行数、占比、趋势。
- [ ] 按项目维度展示贡献分布。

---

## 3. 功能需求

### FR-1：AI Code Tracking API 客户端

- 在 `cursor_api.py` 中新增 `get_ai_code_commits()` 方法。
- 调用 `GET /analytics/ai-code/commits`，支持 `startDate`、`endDate`、`page`、`pageSize` 参数。
- 支持分页遍历（默认 pageSize=1000，遍历至无更多数据）。
- 支持 ETag 缓存（304 Not Modified 不消耗 rate limit）。
- Rate limit：20 requests/minute，需实现退避重试。

### FR-2：数据同步任务

- 新增 `ai_code_sync.py` 模块，定时任务每小时执行。
- 拉取自上次同步以来的新 commit 数据。
- 幂等写入 `ai_code_commits` 表（按 `commit_hash + user_email` 去重）。
- 自动匹配 `project_id`：遍历 `projects` 表的 `git_repos`，与 commit 的 `repoName` 匹配。

### FR-3：数据模型

```sql
CREATE TABLE IF NOT EXISTS ai_code_commits (
    id                      SERIAL PRIMARY KEY,
    commit_hash             TEXT NOT NULL,
    user_id                 TEXT,
    user_email              TEXT NOT NULL,
    repo_name               TEXT NOT NULL,
    branch_name             TEXT,
    project_id              INT REFERENCES projects(id),
    total_lines_added       INT NOT NULL DEFAULT 0,
    total_lines_deleted     INT NOT NULL DEFAULT 0,
    tab_lines_added         INT NOT NULL DEFAULT 0,
    tab_lines_deleted       INT NOT NULL DEFAULT 0,
    composer_lines_added    INT NOT NULL DEFAULT 0,
    composer_lines_deleted  INT NOT NULL DEFAULT 0,
    non_ai_lines_added      INT NOT NULL DEFAULT 0,
    non_ai_lines_deleted    INT NOT NULL DEFAULT 0,
    commit_message          TEXT,
    commit_ts               TIMESTAMPTZ NOT NULL,
    synced_at               TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (commit_hash, user_email)
);

CREATE INDEX IF NOT EXISTS idx_ai_commits_project ON ai_code_commits (project_id, commit_ts);
CREATE INDEX IF NOT EXISTS idx_ai_commits_user ON ai_code_commits (user_email, commit_ts);
CREATE INDEX IF NOT EXISTS idx_ai_commits_repo ON ai_code_commits (repo_name, commit_ts);
```

### FR-4：查询 API

- `GET /api/ai-commits`：管理端查询，支持按 project_id、user_email、日期范围筛选，分页。
- `GET /api/ai-commits/summary`：按项目或成员聚合的汇总（总 AI 行数、AI 占比、commit 数）。
- `GET /api/ai-commits/my`：成员端查询自己的 AI 代码贡献。

---

## 4. 非功能需求

- **幂等**：重复拉取同一 commit 不产生重复记录。
- **容错**：API 不可达时记录错误日志，不影响其他同步任务。
- **性能**：首次全量同步可能数据量大，支持分页拉取；增量同步按日期范围。
- **Rate limit**：遵守 20 req/min 限制，实现指数退避。

---

## 5. 约束与假设

- AI Code Tracking API 为 Alpha 状态（Enterprise only），响应格式可能变化。
- 仅追踪在 Cursor IDE 内提交的 commit；命令行 `git commit` 不在统计范围。
- 多根工作区（multi-root workspace）仅追踪顶层仓库。
- `repoName` 匹配 `projects.git_repos` 时需处理格式差异（如 `org/repo` vs 完整 URL）。

---

## 6. 依赖

- **外部**：Cursor AI Code Tracking API（Enterprise plan）。
- **内部**：cursor-admin-core（DB、Collector 框架、cursor_api.py）；cursor-admin-projects（projects 表）。

---

**维护者**: 团队  
**最后更新**: 2026-02-28  
**状态**: 待实施
