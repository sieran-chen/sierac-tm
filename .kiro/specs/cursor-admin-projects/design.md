# Design: 项目立项与治理

> **目标**：项目 CRUD、白名单、Hook 拦截、会话归属、Git 采集、按项目聚合、GitLab 仓库自动创建的技术设计。  
> **状态**：实施中  
> **最后更新**：2026-02-26

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-projects/requirements.md`
- design: `.kiro/specs/cursor-admin-projects/design.md`
- tasks: `.kiro/specs/cursor-admin-projects/tasks.md`

---

## 1. 数据模型

### 1.1 projects 表

```sql
CREATE TABLE IF NOT EXISTS projects (
    id              SERIAL PRIMARY KEY,
    name            TEXT        NOT NULL,
    description     TEXT        DEFAULT '',
    git_repos       TEXT[]      DEFAULT '{}',       -- Git 仓库地址（可多个）
    workspace_rules TEXT[]      NOT NULL,            -- 工作目录匹配规则（路径前缀，可多条）
    member_emails   TEXT[]      DEFAULT '{}',        -- 参与成员（空 = 全员可用）
    status          TEXT        NOT NULL DEFAULT 'active',  -- active / archived
    gitlab_project_id INT,                           -- GitLab 项目 ID（自动创建时回填）
    repo_url        TEXT        DEFAULT '',           -- 仓库 HTTP clone 地址
    repo_ssh_url    TEXT        DEFAULT '',           -- 仓库 SSH clone 地址
    hook_initialized BOOLEAN    DEFAULT FALSE,        -- Hook 是否已注入仓库
    created_by      TEXT        NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status);
```

### 1.2 git_contributions 表

```sql
CREATE TABLE IF NOT EXISTS git_contributions (
    id              SERIAL PRIMARY KEY,
    project_id      INT         NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author_email    TEXT        NOT NULL,
    commit_date     DATE        NOT NULL,
    commit_count    INT         NOT NULL DEFAULT 0,
    lines_added     INT         NOT NULL DEFAULT 0,
    lines_removed   INT         NOT NULL DEFAULT 0,
    files_changed   INT         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, author_email, commit_date)
);

CREATE INDEX IF NOT EXISTS idx_git_contributions_project ON git_contributions (project_id, commit_date DESC);
CREATE INDEX IF NOT EXISTS idx_git_contributions_author  ON git_contributions (author_email, commit_date DESC);
```

### 1.3 agent_sessions 扩展

```sql
ALTER TABLE agent_sessions ADD COLUMN IF NOT EXISTS project_id INT REFERENCES projects(id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_project ON agent_sessions (project_id, ended_at DESC);
```

---

## 2. API 设计

### 2.1 项目 CRUD（管理端，需 API Key）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects` | 列表（支持 ?status=active） |
| POST | `/api/projects` | 新建 |
| PUT | `/api/projects/{id}` | 编辑 |
| DELETE | `/api/projects/{id}` | 归档（软删除，status→archived） |
| GET | `/api/projects/{id}/summary` | 项目汇总（成本、贡献、参与人） |

**POST Body**：

```json
{
  "name": "Sierac-tm",
  "description": "AI 团队贡献平台",
  "workspace_rules": ["D:\\AI\\Sierac-tm", "/home/dev/sierac-tm"],
  "member_emails": [],
  "created_by": "admin@company.com",
  "auto_create_repo": true,
  "repo_slug": "sierac-tm"
}
```

- `auto_create_repo=true`（默认）：Collector 调用 GitLab API 创建仓库，自动回填 `git_repos`、`repo_url`、`repo_ssh_url`、`gitlab_project_id`，并推送初始化提交（含 `.cursor/` Hook 目录）。
- `auto_create_repo=false`：手动填写 `git_repos`，不调用 GitLab API。

**PUT Body**（编辑时不可更改仓库创建方式）：

```json
{
  "name": "Sierac-tm",
  "description": "AI 团队贡献平台",
  "git_repos": ["git@gitlab.company.com:group/sierac-tm.git"],
  "workspace_rules": ["D:\\AI\\Sierac-tm", "/home/dev/sierac-tm"],
  "member_emails": [],
  "status": "active"
}
```

### 2.2 白名单查询（Hook 端，无 API Key）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects/whitelist` | 返回所有 active 项目的匹配规则 |

**Response**：

```json
{
  "version": "2026-02-25T10:00:00Z",
  "rules": [
    {
      "project_id": 1,
      "project_name": "Sierac-tm",
      "workspace_rules": ["D:\\AI\\Sierac-tm", "/home/dev/sierac-tm"],
      "member_emails": []
    }
  ]
}
```

- `version` 为最新 updated_at，供 Hook 做 If-Modified-Since 缓存。
- `member_emails` 为空表示全员可用；非空则 Hook 需校验当前用户。

### 2.3 Git 贡献查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects/{id}/contributions` | 该项目的 Git 贡献（按人按日） |
| GET | `/api/contributions/my` | 当前用户在所有项目的贡献（成员端） |

---

## 3. Hook 白名单校验流程

```
beforeSubmitPrompt 事件
    │
    ├─ 读本地缓存的白名单（hook_config.json 同目录 whitelist_cache.json）
    │   └─ 缓存过期（>5min）或不存在 → GET /api/projects/whitelist → 更新缓存
    │
    ├─ 遍历 workspace_roots，对每个 root 检查是否匹配任一 rule
    │   └─ 匹配逻辑：root.lower().startswith(rule.lower())（Windows 不区分大小写）
    │              或 root.startswith(rule)（Linux/macOS 区分大小写）
    │
    ├─ 若 member_emails 非空，还需校验当前 user_email 是否在列表中
    │
    ├─ 匹配成功 → {"continue": true}
    │   └─ 记录 matched_project_id 到本地状态，供 stop 上报时使用
    │
    └─ 匹配失败 → {"continue": false, "message": "当前工作目录未在公司项目白名单中。请联系管理员在 Sierac 平台立项。"}
```

### stop 事件上报

在现有 payload 基础上新增 `project_id` 字段：

```json
{
  "event": "session_end",
  "conversation_id": "...",
  "user_email": "...",
  "workspace_roots": ["D:\\AI\\Sierac-tm"],
  "ended_at": 1740000000,
  "duration_seconds": 600,
  "project_id": 1
}
```

Collector 接收时：若 payload 无 project_id，则根据 workspace_roots 匹配 projects 表补填。

---

## 4. Git 采集设计

### 4.1 采集流程

```
定时任务（每小时，在 sync 之后）
    │
    ├─ 遍历 active 项目的 git_repos
    │
    ├─ 对每个 repo：
    │   ├─ 本地 clone 目录：/data/git-repos/{project_id}/{repo_hash}/
    │   ├─ 若不存在 → git clone --bare
    │   ├─ 若已存在 → git fetch --all
    │   │
    │   ├─ git log --since="3 days ago" --format="%ae|%ad|%H" --date=short
    │   │   → 按 author_email + date 分组
    │   │
    │   ├─ 对每个 commit：git diff --stat {hash}^..{hash}
    │   │   → 提取 lines_added, lines_removed, files_changed
    │   │
    │   └─ UPSERT 到 git_contributions（ON CONFLICT 累加）
    │
    └─ 错误处理：单个 repo 失败不影响其他 repo，记录日志
```

### 4.2 性能考虑

- 使用 `--bare` clone 减少磁盘占用。
- 仅扫描最近 3 天（可配置），避免全量扫描。
- Git 操作在独立线程/进程中执行，不阻塞主 sync。

---

## 5. 管理端页面

### 5.1 项目管理页

- 项目列表（名称、状态、成员数、仓库数、创建时间）
- 新建/编辑弹窗（表单）
- 归档操作（确认后 status→archived）

### 5.2 项目详情页

- 基本信息（名称、描述、仓库、规则、成员）
- 成本面板：本周期该项目关联的 agent_sessions 数量、daily_usage 汇总
- 贡献面板：Git 贡献汇总（按成员、按日，图表）
- 参与面板：参与成员列表及各自贡献摘要

### 5.3 导航变更

- 侧边栏新增「项目」入口（替代原「工作目录」）
- 原「工作目录」页改造为「项目参与」视图（按项目聚合，不再展示裸路径）

---

## 6. GitLab 集成设计

### 6.1 模块：`collector/gitlab_client.py`

独立模块，封装所有 GitLab REST API v4 调用。与 `cursor_api.py` 同级，遵循「外部 API 单点出口」原则。

**核心方法**：

| 方法 | GitLab API | 说明 |
|------|-----------|------|
| `create_project(name, path, description, visibility)` | `POST /api/v4/projects` | 在指定 Group 下创建仓库 |
| `push_initial_commit(project_id, files)` | Repository Files API | 推送初始化提交（.cursor/ 目录） |
| `add_members(project_id, emails, access_level)` | `POST /api/v4/projects/:id/members` | 添加仓库成员 |
| `inject_hook_files(project_id, files, branch)` | Repository Files API (commit) | 向已有仓库注入 Hook 文件 |

**配置项**（`.env`）：

```
GITLAB_URL=https://gitlab.company.com
GITLAB_TOKEN=glpat-xxxxxxxxxxxx
GITLAB_GROUP_ID=123
GITLAB_DEFAULT_BRANCH=main
GITLAB_VISIBILITY=private
```

**错误处理**：
- GitLab API 不可达或返回错误 → 项目仍创建（`hook_initialized=false`），管理端展示「仓库创建失败，可重试」。
- Token 权限不足 → 返回明确错误信息。

### 6.2 Hook 模板机制

Collector 维护 `hook_templates/` 目录，包含：

| 文件 | 说明 |
|------|------|
| `hooks.json` | Cursor hooks.json 模板，注册 beforeSubmitPrompt 和 stop |
| `cursor_hook.py` | Hook 脚本（与 `cursor-admin/hook/cursor_hook.py` 同源） |
| `hook_config.json.tmpl` | 配置模板，含 `{{collector_url}}` 和 `{{project_id}}` 占位符 |
| `gitignore.tmpl` | .gitignore 模板，含 `.cursor/hook/.state/` |

立项时 Collector 读取模板、替换变量、通过 GitLab API 推送到新仓库。

### 6.3 立项流程（含仓库创建）

```
POST /api/projects (auto_create_repo=true)
    │
    ├─ 1. 写入 projects 表（status=active, hook_initialized=false）
    │
    ├─ 2. 调用 gitlab_client.create_project()
    │      → 返回 gitlab_project_id, repo_url, repo_ssh_url
    │      → 更新 projects 表
    │
    ├─ 3. 调用 gitlab_client.push_initial_commit()
    │      → 推送 .cursor/ 目录 + .gitignore
    │      → 更新 hook_initialized=true
    │
    ├─ 4. 调用 gitlab_client.add_members()
    │      → 根据 member_emails 添加 Developer 权限
    │
    └─ 5. 返回完整项目信息（含 repo_url、repo_ssh_url）
```

---

## 7. 与其他模块的边界

| 模块 | 交互方式 |
|------|----------|
| cursor-admin-core | 共享 DB；项目 API 在 collector/main.py 中新增路由 |
| cursor-admin-hooks | Hook 脚本增加白名单校验逻辑；上报增加 project_id |
| cursor-admin-incentives | 贡献度计算读取 git_contributions + agent_sessions（按 project_id 聚合） |
| GitLab | 通过 `gitlab_client.py` 单点调用；仓库创建、Hook 注入、成员管理 |

---

## 8. 迁移策略

- 新增 `002_projects.sql` 迁移文件（幂等）。
- 现有 agent_sessions 数据 project_id=NULL，展示为「未归属」。
- 管理员可事后为已有会话批量关联项目（可选，后续迭代）。

---

## 9. 错误处理

- 项目 CRUD：标准 HTTP 错误码（400/404/409）。
- 白名单查询：失败时 Hook 降级为放行（fail-open），避免阻塞成员工作。
- Git 采集：单 repo 失败记录日志，不影响其他 repo 和主 sync。
- GitLab API：调用失败时项目仍可创建（`hook_initialized=false`），管理端展示重试按钮。

---

**维护者**: 团队  
**最后更新**: 2026-02-26
