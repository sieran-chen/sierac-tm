# 端到端验证：立项 → Git commit → Hook 上报 → 计算触发 → 排行榜展示

> 对应 Task 14。在完成 cursor-admin-projects 立项与 Hook 上报的前提下，验证贡献度计算与排行榜全流程。

## 前置条件

- 已完成「项目立项与治理」E2E：至少一个已立项项目、成员 clone 后 Hook 可放行并上报 `project_id`。
- Collector 已配置 Cursor API（用于 daily_usage 同步）、数据库含 `003_incentives.sql` 迁移。
- 管理端可访问 Collector API（`VITE_API_KEY` 一致）。

## 验证步骤

1. **Git 贡献数据**
   - 在已立项项目仓库内产生近期 commit（3 天内），等待 Git 采集周期或重启 Collector 触发采集。
   - 在 DB 中确认：`SELECT * FROM git_contributions WHERE project_id = <id>;` 有对应 `author_email`、`commit_date` 等。

2. **Hook 上报**
   - 成员在匹配工作目录下完成一次 Agent 会话（至 stop 事件）。
   - 在 DB 中确认：`agent_sessions` 中对应记录带正确 `project_id`。

3. **贡献度计算触发**
   - 方式 A：等待定时任务（每日 00:30 / 每周一 01:00 / 每月 1 日 01:30，Asia/Shanghai）。
   - 方式 B：管理端 → 激励规则 → 点击「重新计算」；或调用 `POST /api/incentive-rules/1/recalculate`。
   - 在 DB 中确认：`contribution_scores` 有该周期、该成员的记录（含 `total_score`、`rank`、`hook_adopted`）；`leaderboard_snapshots` 有对应 `period_type`、`period_key` 快照。

4. **排行榜展示**
   - 管理端 → 排行榜 → 选择对应周期（周/月）与周期键。
   - 应看到该成员出现在列表中，排名、总分、代码行数、Commit 数、Hook 状态正确。
   - 切换「仅已接入 Hook」：未接入成员应被过滤或标注。

5. **我的贡献展示**
   - 管理端 → 我的贡献 → 选择该成员、周期与周期键。
   - 应看到得分卡（总分、排名）、维度得分、项目分布、近 8 期趋势；若未接入 Hook，应有提示且会话维度为 0。

## 通过标准

- Git 采集写入 `git_contributions`；Hook 上报写入 `agent_sessions` 且带 `project_id`。
- 计算任务或手动重算后，`contribution_scores`、`leaderboard_snapshots` 有数据。
- 管理端排行榜、我的贡献页展示与 DB 一致，Hook 过滤与状态正确。
