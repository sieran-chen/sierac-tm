# Cursor Hook 颗粒度说明

## 当前设计（会话级）

- **事件**：`beforeSubmitPrompt`（记开始）+ `stop`（记结束）
- **含义**：一次「Agent 会话」一条记录（工作目录 + 时长）
- **问题**：`stop` 触发时机由 Cursor 决定（有时是回复结束，有时要用户点 Stop），**不稳定**；且只反映「在这个目录下跑过会话」，统计意义有限。

---

## 细颗粒度能到什么程度？

Cursor 暴露的钩子大致如下，**越往下事件越细、量越大**：

| 事件 | 触发时机 | 典型 payload | 可统计内容 |
|------|----------|--------------|------------|
| **beforeSubmitPrompt** | 每次用户发一条消息 | conversation_id, generation_id, prompt(片段), attachments, workspace_roots | 每轮对话/每条 prompt 一次 |
| **beforeReadFile** | Agent 要读某个文件前 | conversation_id, generation_id, file_path, workspace_roots | 读了多少次、读了哪些文件 |
| **afterFileEdit** | Agent 改完一个文件后 | conversation_id, generation_id, file_path(等) | 改了多少次、改了哪些文件 |
| **beforeShellExecution** | Agent 要执行 shell 前 | conversation_id, content(命令) | 执行了多少条命令、命令内容 |
| **afterShellExecution** | 命令执行完后 | 同上 + 结果相关 | 可关联到 before 做成功/失败 |
| **beforeMCPExecution** / **afterMCPExecution** | 调用 MCP 工具前后 | conversation_id, 工具名等 | MCP 调用次数、工具类型 |
| **sessionStart** / **sessionEnd** | 会话开始/结束（若支持） | conversation_id, workspace_roots | 会话边界，比 stop 更明确 |
| **stop** | 当前设计用的「结束」 | 同前 | 会话结束（触发不稳定） |

也就是说，**细颗粒度可以到**：

- **按轮次**：每条用户消息一次（beforeSubmitPrompt）→ 可算「请求次数」「按会话的轮数」
- **按读文件**：每次读文件一次（beforeReadFile）→ 可算「读文件次数」「热点文件」
- **按写文件**：每次编辑一次（afterFileEdit）→ 可算「编辑次数」「被改动的文件」
- **按命令**：每次 shell 一次（before/afterShellExecution）→ 可算「命令次数」「命令类型」
- **按 MCP**：每次 MCP 调用一次 → 可算「MCP 使用次数」「按工具统计」

组合起来可以做的统计例如：**某人某天在某个工作目录下发了多少条 prompt、读/写了哪些文件、跑了多少条命令、用了哪些 MCP**，而不再依赖「一次 stop = 一次会话」这种不稳定语义。

---

## 实现上的取舍

| 维度 | 会话级（当前） | 细颗粒度（按事件） |
|------|----------------|---------------------|
| **事件量** | 少（一次会话 1～2 次 hook 调用） | 大（一次会话可能几十次 read/edit/shell） |
| **存储** | 一张 session 表即可 | 需要事件表 + 聚合/汇总（或时序存储） |
| **Hook 脚本** | 只处理 2 种事件 | 要区分多种事件、可能要做批量/异步上报 |
| **对 Cursor 的影响** | 小 | 脚本被调用很频繁，若脚本慢或阻塞会拖慢 Agent |
| **稳定性** | 依赖 stop 语义，不稳定 | 不依赖 stop；用 beforeSubmitPrompt / read / edit 等，触发明确 |

建议若要做细颗粒度：

1. **先选一种主指标**：例如「按 prompt 数」或「按读文件 + 改文件」。
2. **Collector 增加事件接口**：例如 `POST /api/events`，payload 里带 `event_type`（beforeSubmitPrompt / beforeReadFile / afterFileEdit / …）、conversation_id、generation_id、workspace_roots、file_path 等。
3. **Hook 里按事件类型上报**：只上报选中的几种事件，其余直接 `continue`，避免脚本里做重逻辑。
4. **存储与展示**：用事件表按 (user, workspace, day, event_type) 聚合，再做「请求数 / 读文件数 / 编辑数」等报表。

这样就不再依赖「一次 stop」的模糊定义，统计会更稳定、更有意义。
