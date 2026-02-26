# 端到端验证：立项 → Hook → 上报归属 → Git 采集 → 管理端展示

> **Task 27**：立项 → GitLab 仓库 → Hook 注入 → 上报归属（见下文步骤 1–7）。  
> **Task 18**：在上述基础上增加 Git 采集与管理端展示（见步骤 8–9）。

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

8. **Git 采集（Task 18）**
   - 项目已填写 `git_repos`（自动创建时已回填；或手动关联已有仓库）
   - Collector 配置 `GIT_REPOS_ROOT`（可选，默认 `/data/git-repos`）、`GIT_COLLECT_DAYS`（可选，默认 3）
   - 等待定时任务执行（与 sync 同周期，默认每小时），或重启 Collector 触发首次 sync + 采集
   - 在项目仓库内产生近期 commit（3 天内），再次等待采集周期或重启
   - 查询 DB：`SELECT * FROM git_contributions WHERE project_id = <id>;` 应有按 author_email、commit_date 的汇总行

9. **管理端展示（Task 18）**
   - 管理端 → 项目 → 进入该项目详情页
   - 成本面板：应显示该项目关联的会话数、时长
   - 参与面板：应显示参与成员及各自会话摘要
   - 贡献面板：应显示 Git 贡献（按成员、按日）；若尚未有采集数据则为空
   - 项目参与页（原工作目录页）：汇总视图应出现该项目及成员；明细视图会话应带项目名或「未归属」

## 通过标准

- 立项后 GitLab 仓库与 clone 地址可见
- Hook 文件存在于仓库且配置正确
- 白名单目录放行、非白名单拦截
- `agent_sessions.project_id` 正确关联项目
- （Task 18）Git 采集定时任务运行后，`git_contributions` 有数据；管理端项目详情、项目参与页正确展示
