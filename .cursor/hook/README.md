# 工作目录上报 Hook（项目级）

本目录为 Cursor 项目级 Hook，在 **本仓库** 使用 Agent 时，会话结束（stop）会向采集服务上报工作目录与时长，管理端「工作目录」页可看到本项目的使用数据。

- **脚本**：`cursor_hook.py`
- **配置**：`hook_config.json`（`collector_url` 指向采集服务，`user_email` 为空则用 git/环境变量推断）
- **状态**：`.state/` 存会话开始时间，可不提交

若本机没有 `py -3`，可编辑上级目录的 `hooks.json`，将命令改为 `python hook/cursor_hook.py` 或 `python3 hook/cursor_hook.py`。
