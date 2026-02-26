# E2E 测试执行报告

**执行时间**: 2026-02-26  
**环境**: 管理端 http://8.130.50.168:3000，采集 http://8.130.50.168:8000  
**参照**: cursor-admin-projects/E2E_VERIFICATION.md、cursor-admin-incentives/E2E_VERIFICATION.md

---

## 1. 自动化验证结果（API + 健康检查）

| 检查项 | 结果 | 说明 |
|--------|------|------|
| `GET /health` | ✅ 200 | `{"status":"ok"}` |
| `GET /api/projects`（无 key） | ✅ 422 | 正确要求 x-api-key |
| `GET /api/projects`（带 key） | ✅ 200 | 返回 `[]`，接口正常 |
| `GET /api/contributions/my` | ✅ 200 | 返回得分结构，含 hook_adopted、projects 等 |
| `GET /api/contributions/leaderboard` | ✅ 200 | 返回 period_type、period_key、entries（空） |
| `GET /api/sessions/summary-by-project` | ✅ 200 | 返回项目参与汇总（含「未归属」） |
| `GET /api/incentive-rules` | ❌ 500（已做容错） | 若为缺表，代码已改为返回 `[]` 而非 500；重新部署后应为 200。若仍 500，查看 collector 日志 |

**API Key**: 测试使用 `.env.example` 中的默认值 `change_me_internal_key`，与当前部署一致时上述带 key 请求可复现。

---

## 2. 浏览器验证

- 已用 **cursor-ide-browser** 打开管理端并导航至 `/`、`/projects`，页面标题为 "Cursor Admin"，URL 切换正常。
- 因 MCP 返回的 snapshot 为 metadata 类型，未拿到可解析 DOM，以下步骤建议**人工在浏览器中按 spec 逐项操作**。

---

## 3. 立项与治理 E2E（人工对照）

参照 **cursor-admin-projects/E2E_VERIFICATION.md**：

1. **立项**：项目 → 新建项目 → 自动创建（GitLab）→ 填写名称、工作目录规则、仓库 slug、创建人邮箱 → 保存后应有「创建成功」及 clone 地址。
2. **仓库与 Hook**：在 GitLab 确认新仓库含 `.cursor/hook/`（cursor_hook.py、hook_config.json、hooks.json），且 hook_config 中 collector_url、project_id 正确。
3. **成员 clone**：用 clone 地址拉取，确认本地有 `.cursor/hook/`。
4. **白名单放行**：在**匹配**工作目录的路径下用 Cursor 触发 beforeSubmitPrompt → 应放行。
5. **非白名单拦截**：在**不匹配**路径下触发 → 应提示「当前工作目录未在公司项目白名单中…」。
6. **上报归属**：匹配目录下完成一次 Agent 会话至 stop；在 DB 或管理端查看 `agent_sessions` 应有正确 `project_id`。
7. **重试注入**：若立项时 Hook 失败，项目行显示「创建失败」，点重试 → `POST /api/projects/{id}/reinject-hook`，再在 GitLab 确认默认分支含 Hook。
8. **Git 采集**：项目有 git_repos、配置 GIT_REPOS_ROOT/GIT_COLLECT_DAYS，等定时或重启触发采集；近期 commit 后查 DB `git_contributions` 应有数据。
9. **管理端展示**：项目详情页成本/参与/贡献面板、项目参与页汇总与明细（含项目名/未归属）正确。

---

## 4. 激励与贡献 E2E（人工对照）

参照 **cursor-admin-incentives/E2E_VERIFICATION.md**：

1. **Git 贡献**：已立项项目内近期 commit，等采集后 DB `git_contributions` 有对应记录。
2. **Hook 上报**：匹配目录下完成 Agent 会话至 stop，DB `agent_sessions` 带 project_id。
3. **贡献度计算**：定时任务或管理端激励规则「重新计算」/ `POST /api/incentive-rules/1/recalculate`；DB `contribution_scores`、`leaderboard_snapshots` 有数据。
4. **排行榜**：管理端 → 排行榜 → 选周期与周期键，列表含成员、排名、总分、代码行数、Commit 数、Hook 状态；切换「仅已接入 Hook」过滤正确。
5. **我的贡献**：管理端 → 我的贡献 → 选成员、周期与周期键，得分卡、维度得分、项目分布、近 8 期趋势正确；未接入 Hook 时提示且会话维度为 0。

---

## 5. 建议

- **修复 /api/incentive-rules 500**：在服务器上查看 collector 日志（如 `docker compose -f cursor-admin/docker-compose.yml logs collector`），若为「relation incentive_rules does not exist」则确认启动时已执行 `db/migrations/003_incentives.sql`（正常部署下 init_db 会执行）；若为其它异常则按日志修复。
- **完整 E2E**：在浏览器中按 §3、§4 步骤执行并勾选通过项，将结果更新到各 spec 的 E2E_VERIFICATION 或本报告。
