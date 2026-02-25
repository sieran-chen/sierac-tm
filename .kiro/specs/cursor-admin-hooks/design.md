# Design: Cursor Admin Hooks（多语言）

> **目标**：定义 Hook 与 Collector 的契约、配置与多语言实现要点。  
> **状态**：已完成  
> **最后更新**：2026-02-25

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-hooks/requirements.md`
- design: `.kiro/specs/cursor-admin-hooks/design.md`
- tasks: `.kiro/specs/cursor-admin-hooks/tasks.md`

---

## 1. 架构

```
Cursor IDE
  │  beforeSubmitPrompt → 读 stdin → 写本地 state (conversation_id → started_at, workspace_roots)
  │  stop               → 读 stdin → 读 state → 算 duration → POST /api/sessions → 删 state
  │  stdout: {"continue":true}
  ▼
Collector  POST /api/sessions  →  agent_sessions 表
```

---

## 2. 契约：POST /api/sessions

**Request**

- Method: POST
- URL: `{collector_url}/api/sessions`
- Headers: `Content-Type: application/json`
- Body (JSON):

```json
{
  "event": "session_end",
  "conversation_id": "string",
  "user_email": "string",
  "machine_id": "string",
  "workspace_roots": ["path1", "path2"],
  "ended_at": 1234567890,
  "duration_seconds": 120
}
```

- `duration_seconds` 可选（无法计算时为 null 或省略）。
- `workspace_roots` 为数组，可为空。

**Response**

- 204 No Content（成功或失败均不返回 Body，Hook 端不依赖响应体）。

---

## 3. 本地状态（会话开始）

- **路径**：`{state_dir}/{safe_conversation_id}.json`
- **内容**：`{"started_at": unix_ts, "workspace_roots": [...]}`
- **生命周期**：beforeSubmitPrompt 写入；stop 读取并删除。

---

## 4. 配置（hook_config.json）

- **collector_url**：string，必填
- **user_email**：string，可选
- **machine_id**：string，可选
- **timeout_seconds**：number，可选，默认 5
- **state_dir**：string，可选，默认 `~/.cursor/hooks/.state`

配置文件与脚本/JAR 同目录（如 `~/.cursor/hooks/`）；优先读同目录下 hook_config.json，再补环境变量。

---

## 5. hooks.json（Cursor）

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [{ "command": "java -jar ~/.cursor/hooks/cursor_hook.jar" }],
    "stop": [{ "command": "java -jar ~/.cursor/hooks/cursor_hook.jar" }]
  }
}
```

Windows 下 command 可为绝对路径（如 `%USERPROFILE%\.cursor\hooks\cursor_hook.jar`）。

---

## 6. 多语言实现要点

| 项目 | Java | Python |
|------|------|--------|
| 入口 | 从 stdin 读一行 JSON，main 中解析 | 同上 |
| 状态 | 同目录或 state_dir 下文件 | 同上 |
| HTTP | java.net.http.HttpClient | urllib.request 或 httpx |
| 配置 | 同目录 hook_config.json + 环境变量 | 同上 |
| 输出 | 始终打印 `{"continue":true}` | 同上 |

两者行为与契约完全一致，仅实现语言不同。

---

## 7. 部署

- **安装脚本**：install.sh（Unix）、install.ps1（Windows）复制 JAR 或 py、写入 hook_config.json 与用户级 hooks.json。
- **Java**：需 JRE 11+；Maven 打包为 jar-with-dependencies，产物 `cursor_hook.jar`。
- **Python**：需 Python 3.8+；单文件 `cursor_hook.py` 可执行。

---

## 8. 参考文档

- `cursor-admin/hook/java/`、`cursor-admin/hook/cursor_hook.py`
- `.kiro/specs/cursor-admin-core/design.md`

---

**维护者**: 团队  
**最后更新**: 2026-02-25
