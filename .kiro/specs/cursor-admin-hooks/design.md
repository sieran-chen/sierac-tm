# Design: Cursor Admin Hooks（多语言）

> **目标**：定义 Hook 与 Collector 的契约、白名单校验逻辑、配置与多语言实现要点。  
> **状态**：基础版已完成；白名单校验已实现（Python）；Java 版待更新  
> **最后更新**：2026-02-26

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-hooks/requirements.md`
- design: `.kiro/specs/cursor-admin-hooks/design.md`
- tasks: `.kiro/specs/cursor-admin-hooks/tasks.md`

---

## 1. 架构

```
Cursor IDE
  │
  ├─ beforeSubmitPrompt
  │    ├─ 读 stdin (conversation_id, workspace_roots)
  │    ├─ get_whitelist() → 本地缓存 or GET /api/projects/whitelist
  │    ├─ match_whitelist() → 匹配成功: 写 state, continue=true
  │    │                    → 匹配失败: continue=false (拦截)
  │    │                    → 网络错误: fail-open, continue=true
  │    └─ stdout: {"continue": true/false, "message"?: "..."}
  │
  └─ stop
       ├─ 读 stdin (conversation_id)
       ├─ 读本地 state → 计算 duration, 取 project_id
       ├─ POST /api/sessions (含 project_id)
       └─ stdout: {"continue": true}

Collector
  ├─ GET  /api/projects/whitelist  → 返回白名单规则列表
  └─ POST /api/sessions            → 写入 agent_sessions 表
```

---

## 2. 白名单校验逻辑

### 2.1 白名单数据结构（GET /api/projects/whitelist 响应）

```json
{
  "rules": [
    {
      "project_id": "uuid",
      "project_name": "Sierac-tm",
      "workspace_rules": [
        {"type": "prefix", "value": "/home/user/projects/sierac"},
        {"type": "prefix", "value": "D:\\AI\\Sierac-tm"}
      ],
      "member_emails": ["alice@company.com", "bob@company.com"]
    }
  ],
  "generated_at": 1234567890
}
```

- `workspace_rules`：路径匹配规则，支持 `prefix`（前缀匹配）和 `regex`（正则匹配）。
- `member_emails`：可选；为空列表时表示项目对所有成员开放。

### 2.2 本地缓存

- 缓存文件：`{state_dir}/whitelist_cache.json`
- 格式：`{"rules": [...], "generated_at": unix_ts, "cached_at": unix_ts}`
- TTL：`whitelist_ttl_seconds`（默认 300 秒）；超时则重新拉取。
- 拉取失败时：若存在过期缓存，继续使用（fail-open）；若无缓存，fail-open 放行。

### 2.3 匹配算法

```python
def match_whitelist(workspace_roots, user_email, rules) -> tuple[bool, str | None]:
    for rule in rules:
        # 路径匹配
        path_matched = any(
            _match_rule(root, wr)
            for root in workspace_roots
            for wr in rule["workspace_rules"]
        )
        if not path_matched:
            continue
        # 成员匹配（若规则限定成员）
        if rule["member_emails"]:
            if user_email.lower() not in [e.lower() for e in rule["member_emails"]]:
                continue
        return True, rule["project_id"]
    return False, None

def _match_rule(path, rule):
    if rule["type"] == "prefix":
        # Windows 大小写不敏感
        return path.lower().startswith(rule["value"].lower())
    elif rule["type"] == "regex":
        return bool(re.match(rule["value"], path, re.IGNORECASE))
    return False
```

---

## 3. 本地状态（会话开始）

- **路径**：`{state_dir}/{safe_conversation_id}.json`
- **内容**：`{"started_at": unix_ts, "workspace_roots": [...], "project_id": "uuid-or-null"}`
- **生命周期**：`beforeSubmitPrompt` 写入；`stop` 读取并删除。
- `safe_conversation_id`：将 conversation_id 中非法文件名字符替换为 `_`。

---

## 4. 契约：POST /api/sessions

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
  "duration_seconds": 120,
  "project_id": "uuid-or-null"
}
```

- `duration_seconds`：可选（无法计算时省略）。
- `project_id`：可选（fail-open 时为 null）。

**Response**

- 204 No Content（Hook 端不依赖响应体）。

---

## 5. 配置（hook_config.json）

```json
{
  "collector_url": "http://collector:8000",
  "project_id": "{{project_id}}",
  "user_email": "",
  "machine_id": "",
  "timeout_seconds": 5,
  "state_dir": "",
  "whitelist_ttl_seconds": 300,
  "whitelist_enabled": true
}
```

- `project_id`：立项时由 Collector 注入（替换 `{{project_id}}`）。
- `user_email`：为空时从环境变量（`CURSOR_USER_EMAIL`、`GIT_AUTHOR_EMAIL`、`USER`）推断。
- `machine_id`：为空时基于主机名生成。
- `state_dir`：为空时默认 `~/.cursor/hooks/.state`。

---

## 6. hooks.json（Cursor，项目级）

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      { "command": "python3 .cursor/hook/cursor_hook.py" }
    ],
    "stop": [
      { "command": "python3 .cursor/hook/cursor_hook.py" }
    ]
  }
}
```

- 路径相对于项目根目录（Cursor 从项目根执行命令）。
- Windows 下 `python3` 可替换为 `py -3`。
- Java 版：`java -jar .cursor/hook/cursor_hook.jar`。

---

## 7. 多语言实现要点

| 项目 | Java | Python |
|------|------|--------|
| 入口 | 从 stdin 读一行 JSON，main 中解析 | 同上 |
| 白名单校验 | 同上逻辑，Java 实现 | 已实现（cursor_hook.py） |
| 状态 | state_dir 下文件 | 同上 |
| HTTP | java.net.http.HttpClient | urllib.request（无外部依赖） |
| 配置 | 同目录 hook_config.json + 环境变量 | 同上 |
| 输出 | 始终打印 JSON | 同上 |

两者行为与契约完全一致，仅实现语言不同。

---

## 8. 部署方式

### 8.1 项目级（主推）

立项审批通过后，Collector 自动向 GitLab 仓库推送：

```
.cursor/
├── hooks.json          ← 注册事件
└── hook/
    ├── cursor_hook.py  ← Python 实现（或 cursor_hook.jar）
    └── hook_config.json ← 预填 collector_url + project_id
```

成员 clone 仓库后 Hook 自动生效。

### 8.2 用户级（备选）

管理员手动分发，安装到 `~/.cursor/hooks/`；适用于无 GitLab 集成的场景。

- install.sh（Unix）、install.ps1（Windows）复制 JAR 或 py、写入 hook_config.json 与用户级 hooks.json。

---

## 9. 错误处理

| 场景 | 处理 |
|------|------|
| Collector 不可达（白名单拉取） | fail-open：使用过期缓存或直接放行；记录警告 |
| 白名单不匹配 | 返回 `{"continue": false, "message": "..."}`；不写 state |
| 会话上报失败 | 静默忽略；stdout 仍输出 `{"continue": true}` |
| state 文件不存在（stop 时） | 仍尝试上报（无 duration）；不报错 |
| hook_config.json 缺失 | 记录错误；fail-open 放行 |

---

## 10. 参考文档

- `cursor-admin/hook/cursor_hook.py`（Python 实现，含白名单校验）
- `cursor-admin/hook/java/`（Java 实现）
- `cursor-admin/collector/hook_templates/`（项目级注入模板）
- `.kiro/specs/cursor-admin-core/design.md`（/api/sessions 契约）
- `.kiro/specs/cursor-admin-projects/design.md`（/api/projects/whitelist 契约）

---

**维护者**: 团队  
**最后更新**: 2026-02-26
