# 端到端验证：立项 → GitLab 仓库 → Hook 注入 → 上报归属

> 对应 Task 27。按下列步骤在真实环境验证完整流程。

## 前置条件

- Collector 已配置 `GITLAB_URL`、`GITLAB_TOKEN`、`GITLAB_GROUP_ID`
- 管理端可访问 Collector API（`VITE_API_KEY` / `INTERNAL_API_KEY` 一致）
- 至少一个成员在 GitLab 中存在且邮箱与 Cursor 一致

## 验证步骤

1. **立项（自动创建仓库）**
   - 登录管理端 → 项目 → 新建项目
   - 选择「自动创建（GitLab）」，填写项目名称、工作目录规则、仓库 slug、创建人邮箱
   - 保存后应看到「创建成功」及 HTTP/SSH clone 地址，可一键复制

2. **仓库与 Hook**
   - 在 GitLab 中确认新仓库已创建，且含 `.cursor/hook/` 目录（cursor_hook.py、hook_config.json、hooks.json）
   - `hook_config.json` 中 `collector_url`、`project_id` 与当前环境一致

3. **成员 clone**
   - 成员使用 clone 地址拉取仓库到本地
   - 确认本地存在 `.cursor/hook/`，无需额外安装

4. **白名单放行**
   - 成员在**匹配工作目录规则**的路径下打开 Cursor，使用 AI（触发 beforeSubmitPrompt）
   - 应正常放行（无拦截提示）

5. **非白名单拦截**
   - 在**不匹配**工作目录规则的路径下打开同一仓库或其它目录，触发 beforeSubmitPrompt
   - 应看到拦截提示：「当前工作目录未在公司项目白名单中…」

6. **上报归属**
   - 在匹配目录下完成一次 Agent 会话（至 stop 事件）
   - 管理端或 DB 中查看 `agent_sessions`，对应记录应带正确 `project_id`

7. **重试注入（可选）**
   - 若立项时 Hook 注入失败，项目列表该行仓库状态为「创建失败」
   - 点击重试图标，调用 `POST /api/projects/{id}/reinject-hook`
   - 再次在 GitLab 查看默认分支最新提交，应包含 Hook 文件更新

## 通过标准

- 立项后 GitLab 仓库与 clone 地址可见
- Hook 文件存在于仓库且配置正确
- 白名单目录放行、非白名单拦截
- `agent_sessions.project_id` 正确关联项目
