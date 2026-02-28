# Requirements: Cursor Admin Hooks（多语言）

> **目标**：定义 Cursor IDE Hook 的协议与行为，实现 Java（主）与 Python（备）两套实现；`beforeSubmitPrompt` 执行白名单校验（准入拦截），`stop` 上报会话结束事件。  
> **优先级**：P0  
> **预估工作量**：已实现基础版；白名单校验扩展 2–3 天

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-hooks/requirements.md`
- design: `.kiro/specs/cursor-admin-hooks/design.md`
- tasks: `.kiro/specs/cursor-admin-hooks/tasks.md`

---

## 1. 背景与动机

- Cursor 官方 API 不提供「工作目录」「会话时长」；只能通过 Hooks 在会话维度补足。
- 需要粗颗粒度：仅会话开始/结束，不采集每次工具调用，避免大量 token 与存储。
- **新增核心需求**：Hook 是「仓库即准入凭证」机制的执行者——`beforeSubmitPrompt` 必须检查当前工作目录是否属于已立项的公司项目，不匹配则拦截 AI 提交，防止公司 Token 被用于未授权项目。
- 团队主语言为 Java，Hook 需多语言版本（Java 主推、Python 备选）。
- **项目级部署**：立项审批通过后，Hook 文件自动注入到 GitLab 仓库（`.cursor/` 目录），成员 clone 即生效，无需手动安装。

---

## 2. 用户故事

### 2.1 作为管理员——准入拦截

**故事**：成员在未立项的工作目录使用 Cursor Agent 时，Hook 自动拦截并提示，确保公司 Token 只用于公司项目。

**验收标准**：
- [ ] `beforeSubmitPrompt` 从 Collector 获取白名单（含 workspace_rules 与 member_emails）。
- [ ] 当前 `workspace_roots` 与白名单规则不匹配时，返回 `{"continue": false, "message": "..."}` 拦截提交。
- [ ] 白名单本地缓存（TTL 可配置，默认 5 分钟），避免每次请求都调用 Collector。
- [ ] Collector 不可达时 fail-open（放行并记录警告），不阻塞成员正常工作。
- [ ] 拦截时提示信息清晰：「当前工作目录未在公司项目白名单中，请联系管理员立项」。

### 2.2 作为管理员——会话上报

**故事**：部署 Hook 后，每次 Agent 会话结束能收到一条包含工作目录、时长与项目归属的上报。

**验收标准**：
- [ ] Hook 仅监听 `beforeSubmitPrompt`（记录开始 + 白名单校验）与 `stop`（上报结束）。
- [ ] 每次会话仅产生 1 次 HTTP POST，Body 含 `workspace_roots`、`duration_seconds`、`user_email`、`conversation_id`、`project_id`。
- [ ] `project_id` 由 `beforeSubmitPrompt` 匹配白名单时确定，传递给 `stop` 事件使用。
- [ ] 上报失败时静默处理，不阻塞 Cursor；stdout 始终输出 `{"continue":true}`（stop 事件）。

### 2.3 作为成员（Java 团队）

**故事**：使用 Java 实现的 Hook，无需安装 Python，仅需 JRE 11+；clone 项目仓库后 Hook 自动生效。

**验收标准**：
- [ ] 提供 fat JAR，单文件部署；配置通过 `hook_config.json` 或环境变量。
- [ ] 仓库内 `.cursor/hooks.json` 已预配置，clone 后无需额外操作。
- [ ] 白名单校验与会话上报行为与 Python 实现完全一致。

---

## 3. 功能需求

### FR-1：beforeSubmitPrompt — 白名单校验

- 从 stdin 读 JSON，取 `conversation_id`、`workspace_roots`。
- 调用 `get_whitelist()`：优先读本地缓存（`whitelist_cache.json`，TTL 内有效），否则从 `{collector_url}/api/projects/whitelist` 拉取并写缓存。
- 调用 `match_whitelist(workspace_roots, user_email)`：
  - 遍历白名单规则，检查 `workspace_roots` 是否与任一规则的路径前缀/正则匹配。
  - 若规则含 `member_emails`，还需检查当前 `user_email` 是否在列表中。
  - Windows 下路径比较大小写不敏感。
- 匹配成功：
  - 保存 `{conversation_id → started_at, workspace_roots, project_id}` 到本地 state。
  - stdout 输出 `{"continue": true}`。
- 匹配失败：
  - stdout 输出 `{"continue": false, "message": "当前工作目录未在公司项目白名单中，请联系管理员立项"}`。
  - 不写本地 state。
- Collector 不可达（网络错误、超时）：
  - fail-open：保存 state（project_id 为 null），stdout 输出 `{"continue": true}`。
  - 记录警告日志。

### FR-2：stop — 会话上报

- 从 stdin 读 JSON，取 `conversation_id`、`workspace_roots`。
- 读取本地 state（若存在）：取 `started_at`、`project_id`；计算 `duration_seconds`；删除 state 文件。
- 组装 Body（见 FR-4）并 POST 到 `{collector_url}/api/sessions`。
- 无论成功失败，stdout 始终输出 `{"continue": true}`。

### FR-3：其他事件

- 仅输出 `{"continue": true}`，不做任何 I/O。

### FR-4：上报契约（POST /api/sessions）

```json
{
  "event": "session_end",
  "conversation_id": "string",
  "user_email": "string",
  "machine_id": "string",
  "workspace_roots": ["path1", "path2"],
  "ended_at": 1234567890,
  "duration_seconds": 120,
  "project_id": "uuid-or-null"
}
```

- `duration_seconds`：可选（无法计算时省略）。
- `project_id`：可选（fail-open 时为 null；Collector 端可根据 workspace_roots 补填）。

### FR-5：配置（hook_config.json）

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `collector_url` | string | 是 | — | Collector 地址 |
| `project_id` | string | 是 | — | 本仓库对应的项目 ID（立项时注入） |
| `user_email` | string | 否 | 环境变量推断 | 成员邮箱 |
| `machine_id` | string | 否 | 主机名生成 | 机器标识 |
| `timeout_seconds` | number | 否 | 5 | HTTP 超时 |
| `state_dir` | string | 否 | `~/.cursor/hooks/.state` | 会话状态目录 |
| `whitelist_ttl_seconds` | number | 否 | 300 | 白名单缓存有效期 |
| `whitelist_enabled` | bool | 否 | true | 是否启用白名单校验 |

### FR-6：多语言实现

- **Java**：主推；Maven 打包为 fat JAR；行为与上述完全一致。
- **Python**：备选；单文件脚本；供无 Java 环境使用，或作为项目级 Hook 模板。

### FR-7：项目级部署（自动注入）

- 立项审批通过后，Collector 自动向 GitLab 仓库推送 `.cursor/` 目录，包含：
  - `hooks.json`：注册 `beforeSubmitPrompt` 与 `stop` 事件。
  - `hook/cursor_hook.py`（或 `cursor_hook.jar`）：Hook 实现。
  - `hook/hook_config.json`：预填 `collector_url` 与 `project_id`。
- 成员 clone 仓库后 Hook 自动生效，无需手动安装。
- 详见 cursor-admin-projects spec（FR-7、FR-8）。

---

## 4. 非功能需求

- **性能**：脚本/JAR 启动延迟尽量低；白名单本地缓存避免每次请求都调用 Collector。
- **可靠性**：Collector 不可达时 fail-open，不阻塞成员工作。
- **兼容**：遵循 Cursor Hooks 文档（stdin JSON、stdout JSON、hooks.json 格式）。
- **安全**：Hook 不存储或传输敏感信息（仅工作目录路径、邮箱、时长）。

---

## 5. 约束与假设

- Cursor 传入的 payload 中包含 `hook_event_name`、`conversation_id`、`workspace_roots`（以实际 Cursor 文档为准）。
- 白名单校验依赖 Collector 的 `GET /api/projects/whitelist` 接口（由 cursor-admin-projects 实现）。
- 项目级部署方式（`.cursor/` 目录注入）为主推方式；用户级安装（`~/.cursor/hooks/`）作为备选。

---

## 6. 依赖

- **内部**：Collector 提供 `POST /api/sessions`（cursor-admin-core）与 `GET /api/projects/whitelist`（cursor-admin-projects）。
- **内部**：cursor-admin-projects 负责 GitLab 仓库创建与 Hook 文件注入（FR-7）。

---

**维护者**: 团队  
**最后更新**: 2026-02-26  
**状态**: 基础版已实现；白名单校验扩展已实现（Python）；Java 版待更新
