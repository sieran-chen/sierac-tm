# 开源 Cursor Hook 项目分析

已 clone 并分析两个主流开源实现，结论如下。

---

## 1. LangGuard-AI / cursor-otel-hook

**仓库**：<https://github.com/LangGuard-AI/cursor-otel-hook>  
**位置**：`_tmp/cursor-otel-hook/`

### 实现到什么程度

**支持的 Hook 事件（共 14 类）**（见 `packaging/config/hooks.template.json` + `hook_receiver.py`）：

| 事件 | 用途 |
|------|------|
| `sessionStart` / `sessionEnd` | 会话开始/结束（比 stop 更明确） |
| `beforeSubmitPrompt` | 每次用户发消息 |
| `preToolUse` / `postToolUse` / `postToolUseFailure` | 工具调用前后及失败 |
| `beforeShellExecution` / `afterShellExecution` | Shell 命令前后 |
| `beforeMCPExecution` / `afterMCPExecution` | MCP 调用前后 |
| `beforeReadFile` / `afterFileEdit` | 读文件 / 改文件 |
| `subagentStart` / `subagentStop` | 子 Agent 起止 |
| `stop` | 当前轮结束（并触发批量发送） |
| `preCompact` | 上下文压缩（在代码里处理） |

**颗粒度**：每个事件一个 OpenTelemetry span，带完整属性（如 `file_path`、`command`、`tool_name`、`prompt` 等），并维护跨进程的 parent-child 关系（session → subagent → tool）。

**输出**：OTLP 协议，可发到任意 OTEL 后端（LangGuard、Langfuse、Jaeger 等），支持 gRPC、HTTP/protobuf、HTTP/JSON。

**其他**：按 `generation_id` 批量（收到 `stop` 时一次性发送该 generation 的所有 span）、隐私脱敏选项、MDM 部署（macOS pkg、Windows msi）、配置用 JSON 或环境变量。

---

## 2. langchain-ai / Cursor-LangSmith-Integration

**仓库**：<https://github.com/langchain-ai/Cursor-LangSmith-Integration>  
**位置**：`_tmp/Cursor-LangSmith-Integration/`

### 实现到什么程度

**支持的 Hook 事件（见 `hook_handler.py` 的 `HANDLERS`）**：

| 事件 | 处理方式 |
|------|----------|
| `beforeSubmitPrompt` | 创建 root run，记 User Prompt 子 run |
| `afterAgentResponse` | Agent 回复内容 → 子 run |
| `afterAgentThought` | 思考步骤 → 子 run |
| `beforeShellExecution` / `afterShellExecution` | 成对合并为一个 run（FIFO stack 匹配） |
| `beforeMCPExecution` / `afterMCPExecution` | 成对合并为一个 run |
| `beforeReadFile` | 每次读文件一个 run |
| `afterFileEdit` | 每次编辑一个 run（含 lines_added/removed 等） |
| `beforeTabFileRead` / `afterTabFileEdit` | Tab 补全的读/编辑 |
| `stop` | 结束 root run、打 completion 分数、清理该 turn 状态 |

**颗粒度**：每轮对话一个 LangSmith trace（root run），下面挂多个 child runs（User Prompt、Agent Response、Agent Thinking、Shell、MCP、Read、Edit 等）；before/after 成对合并，避免一个操作拆成两个 run。

**输出**：LangSmith API（`langsmith` 库），通过 `conversation_id` 聚成 thread。

**其他**：fail-open、opt-in（`TRACE_TO_LANGSMITH=true`）、支持项目级 `.env`。

---

## 对比小结

| 维度 | cursor-otel-hook | Cursor-LangSmith-Integration |
|------|------------------|------------------------------|
| **事件覆盖** | 最全（含 sessionStart/End、preCompact、subagent、postToolUse 等） | 全（含 Tab 读/编辑、afterAgentThought/Response） |
| **颗粒度** | 每个事件 = 一个 span，细到单次读文件/改文件/命令/MCP | 每轮对话一个 trace，其下按操作类型拆成 runs |
| **输出** | 任意 OTLP 后端（自建/商业均可） | 仅 LangSmith |
| **部署** | 安装脚本 + MDM 包（pkg/msi） | 单文件 Python + hooks.json |
| **稳定性** | 不依赖「stop 语义」；用 sessionStart/End + 各 before/after 即可 | 同上，stop 只用于收尾和打分 |

**结论**：两家都做到了**细颗粒度**——按「每次发问、每次读文件、每次改文件、每次 Shell、每次 MCP」统计，且 **stop 只用于收尾/批量发送，不承担「定义一次会话」的职责**。若我们要做自建统计，可参考 cursor-otel-hook 的事件列表和属性设计，或直接对接其 OTLP 输出；若用 LangSmith，可直接用 Cursor-LangSmith-Integration。

---

---

## 哪个更适配我们（cursor-admin）

**我们的现状**：自建 collector（FastAPI）+ 自建 DB（agent_sessions 等）+ 自建管理端（工作目录、成员、用量、告警）；Hook 当前只上报「会话结束」到 `POST /api/sessions`，无 LangSmith、无 OTEL 后端。

| 维度 | cursor-otel-hook | Cursor-LangSmith-Integration |
|------|------------------|------------------------------|
| **输出对接** | OTLP → 任意后端 | 仅 LangSmith API |
| **我们能否直接用** | 需先接 OTLP（加 collector/导出到我们 API）或改其 exporter | 仅当我们要用 LangSmith 时才有用 |
| **事件/颗粒度** | 最全（session、tool、shell、MCP、read/edit、subagent、preCompact） | 全（含 afterAgentThought/Response、Tab） |
| **部署形态** | 安装脚本 + MDM 包，可集中下发 | 单文件 + hooks.json，轻量 |
| **与现有 collector 的关系** | 不直接对接；要么我们接 OTLP，要么 fork 成「发我们 API」 | 不对接；数据进 LangSmith，不进我们 DB |

**结论**：

- **Cursor-LangSmith-Integration**：不适合。我们不做 LangSmith 观测，数据进他们云、不进我们库，管理端也读不到。
- **cursor-otel-hook**：**更适配**，但需要选一种用法：
  1. **接 OTLP**：在我们侧跑一个 OTEL Collector，接收 OTLP 再转写我们 DB/API。事件最全、无需改 hook 代码，但要多维护一个组件和映射逻辑。
  2. **参考事件列表、自建上报**（推荐）：沿用 cursor-otel-hook 的 **事件清单和 payload 设计**，在我们现有 `.cursor/hook` 里扩展——对 `beforeSubmitPrompt` / `beforeReadFile` / `afterFileEdit` / `beforeShellExecution` / `afterShellExecution` / `beforeMCPExecution` / `afterMCPExecution` 等做轻量上报到我们自己的 `POST /api/events`（或类似），collector 落我们自己的事件表并做聚合。这样：**只维护一套 collector + 一套 hook**，数据全在我们库里，管理端可做细颗粒统计，且不依赖「stop」语义。

**推荐路线**：以 **cursor-otel-hook 的事件集为参考**，在我们 collector 增加事件接口与表，在项目级 hook（`.cursor/hook/cursor_hook.py`）里按需订阅部分事件并上报到我们 API；不直接采用 LangSmith 方案，也不必须上整套 OTLP（除非后续要对接 Jaeger/Langfuse 等）。

---

## 参考文件

- `_tmp/cursor-otel-hook/README.md` — 功能与事件说明  
- `_tmp/cursor-otel-hook/src/cursor_otel_hook/hook_receiver.py` — 事件处理与 span 属性  
- `_tmp/cursor-otel-hook/packaging/config/hooks.template.json` — 注册的 hook 列表  
- `_tmp/Cursor-LangSmith-Integration/hook_handler.py` — 各事件 handler 与 run 结构  
- `_tmp/Cursor-LangSmith-Integration/README.md` — 配置与启用方式  
