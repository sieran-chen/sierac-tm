# Requirements: Cursor Admin Hooks（多语言）

> **目标**：定义 Cursor IDE Hook 的协议与行为，实现 Java（主）与 Python（备）两套实现，每次 Agent 会话仅上报 1 条记录。  
> **优先级**：P0  
> **预估工作量**：已实现，维护 1–2 天/迭代

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-hooks/requirements.md`
- design: `.kiro/specs/cursor-admin-hooks/design.md`
- tasks: `.kiro/specs/cursor-admin-hooks/tasks.md`

---

## 1. 背景与动机

- Cursor 官方 API 不提供「工作目录」「会话时长」；只能通过 Hooks 在会话维度补足。
- 需要粗颗粒度：仅会话开始/结束，不采集每次工具调用或文件编辑，避免大量 token 与存储。
- 团队主语言为 Java，对外 Hook 需多语言版本（Java 主推、Python 备选）。

---

## 2. 用户故事

### 2.1 作为管理员

**故事**：部署 Hook 到成员机器后，每次 Agent 会话结束能收到一条包含工作目录与时长的上报，且不影响 Cursor 正常使用。

**验收标准**：
- [ ] Hook 仅监听 beforeSubmitPrompt（记录开始）与 stop（上报结束）。
- [ ] 每次会话仅产生 1 次 HTTP POST，Body 含 workspace_roots、duration_seconds（若可算）、user_email、conversation_id 等。
- [ ] 上报失败时静默处理，不阻塞 Cursor；stdout 始终输出 `{"continue":true}`。

### 2.2 作为成员（Java 团队）

**故事**：使用 Java 实现的 Hook，无需安装 Python，仅需 JRE 11+。

**验收标准**：
- [ ] 提供 fat JAR，单文件部署；配置通过 hook_config.json 或环境变量。
- [ ] 安装脚本（install.sh / install.ps1）可复制 JAR 并写入 hooks.json，命令为 `java -jar .../cursor_hook.jar`。

---

## 3. 功能需求

### FR-1：事件与协议

- **beforeSubmitPrompt**：从 stdin 读 JSON，取 conversation_id、workspace_roots；在本地 state_dir 下按 conversation_id 保存开始时间与 workspace_roots；stdout 输出 `{"continue":true}`。
- **stop**：从 stdin 读 JSON，取 conversation_id、workspace_roots；若存在该 conversation_id 的本地状态则计算 duration_seconds，并删除本地状态；组装 Body 发送 POST /api/sessions；stdout 输出 `{"continue":true}`。
- **其他事件**：仅输出 `{"continue":true}`，不做任何 I/O。

### FR-2：上报契约

- **URL**：config.collector_url + `/api/sessions`。
- **Method**：POST。
- **Body**：JSON，见 design.md。
- **超时**：可配置（如 5s）；失败静默，不重试阻塞。

### FR-3：配置

- **collector_url**：必填。
- **user_email**：可选；为空则从环境变量（CURSOR_USER_EMAIL、GIT_AUTHOR_EMAIL 等）或系统用户推断。
- **machine_id**：可选；为空则基于主机名等生成。
- **state_dir**：会话开始状态存放目录，默认 `~/.cursor/hooks/.state`。
- **timeout_seconds**：HTTP 超时。

### FR-4：多语言实现

- **Java**：主推；Maven 打包为 fat JAR；行为与上述一致。
- **Python**：备选；单文件脚本，行为与 Java 一致；供无 Java 环境使用。

---

## 4. 非功能需求

- **性能**：脚本/JAR 启动与解析 stdin 延迟尽量低，不拖慢 Cursor。
- **兼容**：遵循 Cursor Hooks 文档（stdin JSON、stdout JSON、hooks.json 格式）。

---

## 5. 约束与假设

- Cursor 传入的 payload 中包含 hook_event_name、conversation_id、workspace_roots（以实际 Cursor 文档为准）。
- 部署方式由管理员负责（手动或 MDM）；本 spec 不规定企业 MDM 具体流程。

---

## 6. 依赖

- 内部：collector 提供 POST /api/sessions 且契约与本 spec 一致（见 cursor-admin-core design）。

---

## 7. 参考文档

- Cursor 官方 Hooks 文档
- `docs/ARCHITECTURE.md`
- `.kiro/specs/cursor-admin-core/design.md`（/api/sessions 契约）

---

**维护者**: 团队  
**最后更新**: 2026-02-25
