# 工作目录上报 Hook（项目级）

本目录为 Cursor 项目级 Hook，在 **本仓库** 使用 Agent 时，会话结束（stop）会向采集服务上报工作目录与时长，管理端「项目参与」「项目详情」可看到本项目的成本与参与成员。

- **脚本**：`cursor_hook.py`
- **配置**：`hook_config.json`（`collector_url` 指向采集服务，`user_email` 为空则用 git/环境变量推断）
- **状态**：`.state/` 存会话开始时间，可不提交

**命令**：上级目录 `hooks.json` 中默认为 `py -3 .cursor/hook/cursor_hook.py`。若管理端一直无数据，可改为：
- `python .cursor/hook/cursor_hook.py`
- 或 `python3 .cursor/hook/cursor_hook.py`  
（视本机 Python 命令而定；Cursor 调用 Hook 时若命令执行失败则不会上报。）

**什么叫「完整 Agent 会话」**：在 Cursor 里用 **Composer / Agent**（不是单纯 Chat）发起一次对话，让 Agent 跑完（例如让它改代码、执行任务），然后**结束/关闭该对话**。结束时会触发 `stop` 事件，Hook 才会上报这条会话；只打开 Composer 不结束不会上报。

**立项且仍无数据时排查**：
1. **工作目录规则**：在管理端打开该项目详情页，看「基本信息」里的「工作目录规则」。你本机打开该仓库的根路径必须与其中一条**前缀匹配**（不区分大小写）。规则末尾多打了一个「。」也会导致不匹配（服务端与 Hook 已做兼容：会自动去掉规则末尾的。，等符号）。
2. **Hook 是否被执行**：在本仓库用 Cursor 完整跑完一次 Agent 会话（见上）再刷新项目详情；若仍为 0，在终端执行 `echo "{\"hook_event_name\":\"stop\",\"conversation_id\":\"test-1\",\"workspace_roots\":[\"D:\\\\AI\\\\Sierac-tm\"]}" | python .cursor/hook/cursor_hook.py` 看是否有报错。
