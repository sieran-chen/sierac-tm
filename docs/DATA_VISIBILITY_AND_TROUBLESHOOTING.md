# 数据可见性条件与排查

> 说明：用量、支出、Git 贡献、Hook 四类数据在什么条件下会展示、不展示时如何排查。  
> 对应 Spec：`.kiro/specs/cursor-admin-loop-and-data/`

---

## 一、用量总览

- **数据来源**：Cursor Admin API `get_daily_usage` → 定时同步写入 `daily_usage` 表。
- **可展示条件**：  
  - 已配置 `CURSOR_API_TOKEN`（Team/Enterprise Admin API Key）。  
  - 同步任务已至少成功执行一次（默认每 60 分钟随 run_full_sync 执行）。
- **不展示时排查**：  
  - 检查环境变量 `CURSOR_API_TOKEN` 是否配置、是否有效。  
  - 查看 collector 日志是否有 `sync_daily_usage failed` 或 401/5xx。  
  - 数据库：`SELECT COUNT(*) FROM daily_usage;` 是否有行。

---

## 二、支出管理

- **数据来源**：Cursor Admin API `get_spend`（POST /teams/spend）→ 定时同步写入 `spend_snapshots` 表。
- **可展示条件**：  
  - 已配置 `CURSOR_API_TOKEN`。  
  - 同步任务已至少成功执行一次。  
  - Cursor 团队套餐支持「支出」接口并返回 `teamMemberSpend`；部分套餐可能无该数据。
- **不展示时排查**：  
  - 环境变量：`CURSOR_API_TOKEN` 已配置且非空。  
  - 日志：是否有 `sync_spend failed` 或 401/5xx。  
  - 直接调 Cursor API：用同 token 请求 `POST {CURSOR_API_URL}/teams/spend`，看是否返回 `teamMemberSpend` 数组。  
  - 数据库：`SELECT COUNT(*) FROM spend_snapshots;` 是否有行。

---

## 三、Git 贡献

- **数据来源**：采集服务对已立项且填写了「关联仓库」的项目执行 `git clone/fetch` + `git log` → 写入 `git_contributions` 表。
- **可展示条件**：  
  - 项目已填写「关联仓库」（`git_repos` 非空）。  
  - 采集服务已配置 `GIT_REPOS_ROOT`（可写目录，默认 `/data/git-repos`）；Docker 建议挂载卷 `git_repos_data:/data/git-repos`。  
  - 运行环境中已安装 `git`（Collector 镜像已包含）。  
  - 定时任务（在 sync 之后）已至少执行一次 `run_git_collect`。  
  - 仓库可被采集服务访问（公开仓库或已配置凭证的私有仓库）。
- **不展示时排查**：  
  - 项目配置：`SELECT id, name, git_repos FROM projects WHERE status='active';` 目标项目 `git_repos` 非空且 URL 正确。  
  - 环境变量：`GIT_REPOS_ROOT`、`GIT_COLLECT_DAYS`；Docker 挂载 `git_repos_data:/data/git-repos`。  
  - 环境：容器内执行 `git --version` 确认存在。  
  - 日志：collector 中 `git_collector` 是否有 `clone failed` / `fetch failed` / `git log failed`。  
  - 数据库：`SELECT COUNT(*) FROM git_contributions WHERE project_id=?;` 是否有行。

---

## 四、Hook 上报（项目参与、成本归属、贡献得分/排行）

- **数据来源**：成员在匹配工作目录下使用 Cursor，Hook 的 `stop` 事件 POST /api/sessions → `agent_sessions` 表（含 `project_id`）。
- **可展示条件**：  
  - 项目已在「项目管理」立项，且工作目录规则与成员实际路径一致。  
  - 成员在对应目录下使用 Cursor，且已安装并启用 Hook（`.cursor/hook/` 或项目级 Hook）。  
  - Hook 能访问 Collector 的 `/api/projects/whitelist` 与 `/api/sessions`；beforeSubmitPrompt 匹配成功并写入 project_id，stop 时上报。
- **不展示时排查**：  
  - 项目管理中该项目的「工作目录规则」是否包含成员实际打开的工作目录路径。  
  - 成员是否在已立项项目目录下打开 Cursor；Hook 文件是否存在于 `.cursor/hook/` 且 hooks.json 已注册。  
  - 网络：Hook 所在环境能否访问 Collector 的 whitelist 与 sessions 接口。  
  - 数据库：`SELECT COUNT(*) FROM agent_sessions WHERE ended_at >= NOW() - INTERVAL '7 days';` 是否有行。

---

## 五、闭环健康 / Hook 状态

- **含义**：「闭环已接通」指最近 N 天（如 7 天）内存在至少一条 `agent_sessions` 记录。
- **接口**：GET /api/health/loop（需 x-api-key）返回 `loop_ok`、`last_session_at`、`sessions_count_7d`、`members_with_sessions_7d` 等；当无会话时 `loop_ok` 为 false。
- **用途**：管理端可据此展示「尚未检测到 Hook 上报」引导或「已接通」状态；详见 `.kiro/specs/cursor-admin-loop-and-data/`。

---

## 六、相关文档

- 业务闭环与 Hook 的关系：`docs/BUSINESS_LOOP_AND_HOOK.md`
- 将本仓库纳入平台：`docs/SIERAC-TM-ONBOARDING.md`
- Spec：`.kiro/specs/cursor-admin-loop-and-data/`

---

**维护者**：团队  
**最后更新**：2026-02-26
