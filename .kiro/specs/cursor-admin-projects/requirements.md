# Requirements: 项目立项与治理

> **目标**：以「项目」为一等实体，实现立项白名单、Hook 准入拦截、成本归属、贡献归集，形成「立项 → 使用 → 产出 → 评估」闭环。  
> **优先级**：P0（Phase 0，所有贡献可视化与激励的前置）  
> **预估工作量**：5–8 天

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-projects/requirements.md`
- design: `.kiro/specs/cursor-admin-projects/design.md`
- tasks: `.kiro/specs/cursor-admin-projects/tasks.md`
- status: `.kiro/specs/SPEC_TASKS_SCAN.md`

---

## 1. 背景与动机

### 1.1 当前问题

- 「工作目录」页展示裸路径，无业务含义，无法回答「谁在哪个项目贡献了什么」。
- 公司 Cursor Token 无准入控制，成员可在任意目录（含私人项目）使用。
- 用量/支出数据按人汇总，无法按项目归集成本，无法评估投入产出比。
- 贡献数据（Git、Hook、API）缺少归属锚点，无法聚合到业务实体。

### 1.2 设计目标

- 管理员可在平台「立项」——注册项目名称、Git 仓库、工作目录匹配规则、参与成员。
- Hook 据白名单放行或拦截，确保公司 Token 只用于已立项项目。
- 所有数据（用量、支出、会话、Git 贡献）按项目归集，支持按项目查看成本与产出。
- 为后续贡献可视化（Phase 1）与激励（Phase 2）提供「项目」这一核心实体。

---

## 2. 用户故事

### 2.1 作为管理员——立项

**故事**：我要在平台注册一个公司项目，填写项目名称、关联的 Git 仓库地址、工作目录匹配规则，这样成员只能在已立项项目中使用公司 Cursor。

**验收标准**：
- [ ] 管理端有「项目管理」页面，支持新建/编辑/归档项目。
- [ ] 项目信息包含：名称、描述、Git 仓库地址（可多个）、工作目录匹配规则（路径前缀，可多条）、参与成员（可选，不填则全员可用）、状态（active / archived）。
- [ ] 立项后白名单立即生效，Hook 可查询到该项目的规则。

### 2.2 作为管理员——按项目看成本

**故事**：我要按项目查看本周期的 Token 消耗和支出，评估每个项目的投入。

**验收标准**：
- [ ] 管理端有「项目成本」视图，按项目聚合展示用量与支出。
- [ ] 支持按时间范围筛选。
- [ ] 未归属项目的用量单独展示为「未归属」。

### 2.3 作为管理员——按项目看贡献

**故事**：我要按项目查看成员的代码贡献（commit 数、增删行数）和参与情况。

**验收标准**：
- [ ] 管理端项目详情页展示该项目的贡献汇总（按成员、按时间）。
- [ ] 数据来源：Git 仓库扫描（commit/diff）+ Hook 会话上报。
- [ ] 支持按时间范围筛选。

### 2.4 作为成员——看到自己参与的项目

**故事**：我要看到自己参与了哪些公司项目，以及在每个项目上的贡献。

**验收标准**：
- [ ] 成员端（或管理端成员视角）有「我的项目」视图。
- [ ] 展示我参与的已立项项目列表及各项目的贡献摘要。

### 2.5 作为成员——被拦截时得到友好提示

**故事**：当我在非公司项目目录使用 Cursor Agent 时，应收到友好提示而非静默失败。

**验收标准**：
- [ ] Hook 拦截时返回 `{"continue": false, "message": "..."}` 并包含可读提示。
- [ ] 提示内容说明原因并引导联系管理员立项。

---

## 3. 功能需求

### FR-1：项目 CRUD

- 管理端页面 + Collector API（`/api/projects`）。
- 字段：name, description, git_repos (text[]), workspace_rules (text[]), member_emails (text[], 可选), status, created_by, created_at, updated_at。
- 支持 active / archived 状态切换（归档后白名单失效，历史数据保留）。

### FR-2：白名单查询 API

- `GET /api/projects/whitelist`：返回所有 active 项目的 workspace_rules 列表（供 Hook 调用）。
- 响应格式轻量，便于 Hook 缓存（含版本号或 ETag）。
- 无需 API Key 鉴权（Hook 端无密钥），但建议限制来源 IP 或使用轻量签名。

### FR-3：Hook 白名单校验

- Hook 在 `beforeSubmitPrompt` 事件中：
  1. 获取白名单（本地缓存 + 定时刷新，如每 5 分钟）。
  2. 检查当前 `workspace_roots` 是否匹配任一规则。
  3. 匹配 → `{"continue": true}`；不匹配 → `{"continue": false, "message": "..."}`。
- `stop` 事件上报时，标记所属项目 ID（匹配到的项目）。

### FR-4：会话归属项目

- `agent_sessions` 表新增 `project_id` 字段（nullable，FK → projects）。
- Hook 上报时或 Collector 接收时，根据 workspace_rules 匹配并写入 project_id。
- 未匹配的会话 project_id 为 NULL（历史数据兼容）。

### FR-5：按项目聚合查询

- 管理端 API 支持按 project_id 筛选/聚合：sessions、daily_usage（通过会话关联）、贡献数据。
- 新增 `/api/projects/{id}/summary`：该项目的成本、贡献、参与人数汇总。

### FR-6：Git 仓库采集（基础）

- Collector 定时任务：对每个 active 项目的 git_repos，执行 `git log` / `git diff --stat` 提取近期 commit。
- 写入 `git_contributions` 表：project_id, author_email, commit_date, commit_count, lines_added, lines_removed, files_changed。
- 首期仅支持通过 SSH/HTTPS clone 到服务器本地的仓库；后续可扩展 GitHub/GitLab API。

### FR-7：立项自动创建 GitLab 仓库

- 管理员立项时可选择「自动创建仓库」或「关联已有仓库」。
- 选择「自动创建」时：
  1. Collector 调用 GitLab API 在指定 Group 下创建新仓库。
  2. 自动推送初始化提交，包含 `.cursor/hooks.json`、`.cursor/hook/cursor_hook.py`、`.cursor/hook/hook_config.json`、`.gitignore`。
  3. 根据 `member_emails` 自动添加仓库成员（Developer 权限）。
  4. 自动回填 `git_repos`、`repo_url`、`repo_ssh_url` 字段。
- 选择「关联已有仓库」时：手动填写仓库地址，可通过「注入 Hook」操作向已有仓库提交 `.cursor/` 目录。
- 立项成功后管理端展示仓库 clone 地址，可一键复制。

### FR-8：Hook 模板自动注入

- Collector 维护一套 Hook 模板文件（`hook_templates/`），立项时动态替换 `collector_url`、`project_id` 等变量后注入仓库。
- 成员 clone 仓库后 Cursor 自动识别 `.cursor/hooks.json`，Hook 即刻生效，无需额外安装。
- 模板更新时，可通过管理端「重新注入 Hook」操作批量更新已有项目仓库。

---

## 4. 非功能需求

- **性能**：白名单查询 < 100ms；Git 扫描不阻塞主同步任务；GitLab API 调用异步执行，不阻塞立项响应。
- **兼容性**：现有 agent_sessions 数据（project_id=NULL）正常展示为「未归属」。
- **安全**：白名单 API 不暴露项目详情，仅返回匹配规则；Git 仓库凭证安全存储；GitLab Token 仅存于服务端 `.env`，不暴露给客户端。
- **可靠性**：GitLab API 调用失败时项目仍可创建（仓库创建标记为失败，可重试），不阻塞立项流程。

---

## 5. 约束与假设

- Git 托管平台为 **GitLab**（自建或 gitlab.com），通过 GitLab REST API v4 操作。
- 立项时自动创建仓库需配置 `GITLAB_URL`、`GITLAB_TOKEN`（api scope）、`GITLAB_GROUP_ID`。
- workspace_rules 为路径前缀匹配（如 `D:\AI\Sierac-tm`、`/home/dev/owlclaw`），大小写按 OS 处理。
- 白名单缓存在 Hook 端，刷新间隔可配置（默认 5 分钟）。
- Hook 模板随 Collector 部署，更新模板需重新部署 Collector 或手动触发重新注入。

---

## 6. 依赖

- **内部**：cursor-admin-core（DB、Collector、管理端框架）；cursor-admin-hooks（Hook 脚本扩展）。
- **外部**：Git CLI（服务器需安装 git）；GitLab API（需 Token 配置）。

---

## 7. 参考文档

- `docs/ARCHITECTURE.md` §五（核心实体：项目）
- `.cursor/rules/sierac_core.mdc` §四（项目立项与治理层）
- `.kiro/specs/cursor-admin-core/`
- `.kiro/specs/cursor-admin-hooks/`

---

**维护者**: 团队  
**最后更新**: 2026-02-26  
**状态**: 实施中
