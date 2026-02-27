# Tasks: Cursor Admin Hooks（多语言）

> **状态**：Phase 1–3 已完成（含 Java 白名单校验）  
> **最后更新**：2026-02-26

---

## 进度概览

- **总任务数**：13
- **已完成**：Phase 1–2（9 项）+ Phase 3 Python（2 项）+ Phase 3 Java（2 项）
- **待完成**：无

---

## 1. Phase 1：协议与 Python 实现（已完成）

- [x] 1.1 定义 POST /api/sessions 的 Request Body 契约（与 collector 一致）
- [x] 1.2 实现 cursor_hook.py：beforeSubmitPrompt 写 state；stop 读 state、算 duration、POST、删 state；始终 stdout `{"continue":true}`
- [x] 1.3 支持 hook_config.json 与环境变量（collector_url、user_email、machine_id、state_dir、timeout_seconds）
- [x] 1.4 提供 install.sh、install.ps1，写入 hooks.json

---

## 2. Phase 2：Java 实现与安装（已完成）

- [x] 2.1 实现 Java 版：CursorHook.java，逻辑与 Python 一致
- [x] 2.2 Maven 打包 fat JAR，产物 cursor_hook.jar
- [x] 2.3 install.sh / install.ps1 优先复制 cursor_hook.jar，hooks.json 命令改为 `java -jar`
- [x] 2.4 若未找到 JAR 则提示先执行 mvn package

---

## 3. Phase 3：白名单校验扩展

### 3.1 Python 实现（已完成）

- [x] 3.1 cursor_hook.py 的 beforeSubmitPrompt 增加白名单校验逻辑：
  - [x] `get_whitelist()`：本地缓存（whitelist_cache.json，TTL 可配置）+ 从 Collector 拉取
  - [x] `match_whitelist()`：路径前缀/正则匹配 + 成员邮箱匹配（Windows 大小写不敏感）
  - [x] 匹配失败返回 `{"continue": false, "message": "..."}` 拦截提交
  - [x] Collector 不可达时 fail-open（放行 + 记录警告）
- [x] 3.2 hook_config.json 增加 `whitelist_ttl_seconds`、`whitelist_enabled` 字段
- [x] 3.3 beforeSubmitPrompt 匹配成功时将 project_id 写入本地 state，stop 事件读取并上报

### 3.2 Java 实现（已完成）

- [x] 3.4 Java 版 CursorHook.java 同步实现白名单校验逻辑（与 Python 行为一致）：
  - [x] 本地缓存读写（JSON 文件，TTL 检查）
  - [x] GET /api/projects/whitelist 拉取
  - [x] 路径匹配（前缀 + 正则，Windows 大小写不敏感）
  - [x] fail-open 处理
- [x] 3.5 Java 版 hook_config.json 支持 `whitelist_ttl_seconds`、`whitelist_enabled`、`project_id` 字段

---

## 4. 验收清单

- [x] Python：`echo '{"hook_event_name":"stop",...}' | python3 cursor_hook.py` 输出 `{"continue":true}`
- [x] Java：同上通过 `java -jar cursor_hook.jar` 输出一致
- [x] 部署后 Cursor 触发 stop 时 collector 收到 POST 且 agent_sessions 有记录
- [x] Python：白名单不匹配时返回 `{"continue": false, ...}`，Cursor 拦截提交
- [x] Python：Collector 不可达时 fail-open，不阻塞成员
- [x] Java：白名单校验行为与 Python 一致（依赖 3.4 完成）

---

## 5. 参考文档

- `.kiro/specs/cursor-admin-hooks/requirements.md`
- `.kiro/specs/cursor-admin-hooks/design.md`
- `cursor-admin/hook/cursor_hook.py`（Python 实现）
- `cursor-admin/hook/java/`（Java 实现）

---

**维护者**: 团队  
**最后更新**: 2026-02-26
