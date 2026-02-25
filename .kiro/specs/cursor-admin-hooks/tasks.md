# Tasks: Cursor Admin Hooks（多语言）

> **状态**：已完成  
> **最后更新**：2026-02-25

---

## 进度概览

- **总任务数**：见下方
- **已完成**：Phase 1–2
- **进行中**：无

---

## 1. Phase 1：协议与 Python 实现（已完成）

- [x] 1.1 定义 POST /api/sessions 的 Request Body 契约（与 collector 一致）
- [x] 1.2 实现 cursor_hook.py：beforeSubmitPrompt 写 state；stop 读 state、算 duration、POST、删 state；始终 stdout `{"continue":true}`
- [x] 1.3 支持 hook_config.json 与环境变量（collector_url、user_email、machine_id、state_dir、timeout_seconds）
- [x] 1.4 提供 install.sh、install.ps1，写入 hooks.json（command 为 python3 ~/.cursor/hooks/cursor_hook.py）

---

## 2. Phase 2：Java 实现与安装（已完成）

- [x] 2.1 实现 Java 版：CursorHook.java，逻辑与 Python 一致（stdin 一行 JSON、state 文件、HTTP POST）
- [x] 2.2 Maven 打包 fat JAR（jar-with-dependencies），产物 cursor_hook.jar
- [x] 2.3 install.sh / install.ps1 优先复制 cursor_hook.jar，hooks.json 命令改为 `java -jar ~/.cursor/hooks/cursor_hook.jar`
- [x] 2.4 若未找到 JAR 则提示先执行 mvn -f hook/java/pom.xml package

---

## 3. 验收清单

- [x] Python：echo '{"hook_event_name":"stop",...}' | python3 cursor_hook.py 输出 `{"continue":true}`
- [x] Java：同上通过 java -jar cursor_hook.jar 输出一致
- [x] 部署后 Cursor 触发 stop 时 collector 收到 POST 且 agent_sessions 有记录

---

## 4. 参考文档

- `.kiro/specs/cursor-admin-hooks/requirements.md`
- `.kiro/specs/cursor-admin-hooks/design.md`

---

**维护者**: 团队  
**最后更新**: 2026-02-25
