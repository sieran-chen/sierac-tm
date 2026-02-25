# Design: Cursor Admin 团队激励（预留）

> **目标**：为贡献度排行与评分预留架构与数据模型方向。  
> **状态**：预留，未实施  
> **最后更新**：2026-02-25

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-incentives/requirements.md`
- design: `.kiro/specs/cursor-admin-incentives/design.md`
- tasks: `.kiro/specs/cursor-admin-incentives/tasks.md`

---

## 1. 架构方向

- **数据来源**：仅用现有表 `daily_usage`、`agent_sessions`、`spend_snapshots` 做聚合，不新增采集链路。
- **计算时机**：在 collector 的 sync 之后增加「贡献度计算」任务（或独立定时任务），按配置周期（日/周/月）写入得分与排行。
- **扩展表（建议）**：
  - `contribution_scores`：周期类型、周期标识（如 2026-W08）、user_email、各维度得分与总分、排名。
  - `incentive_rules`：规则名称、权重配置（JSON）、周期、启用状态（与 alert_rules 类似）。
  - `leaderboard_snapshots`：可选，历史排行快照，便于审计与展示趋势。

---

## 2. 与核心平台边界

- 激励逻辑与「用量/告警」解耦：独立模块或独立服务，通过读 DB 与写扩展表与核心平台交互。
- 不修改 core 的 sync 与 alert 逻辑；仅新增「计算任务」与 API/页面。

---

## 3. 实现优先级（启动时再定）

- Phase 1：指标定义与 contribution_scores 表、单周期计算与 API。
- Phase 2：可配置规则（incentive_rules）、多维度权重。
- Phase 3：排行快照、成员端「我的得分」页面。

---

## 4. 参考文档

- `docs/ARCHITECTURE.md` §5
- `.kiro/specs/cursor-admin-core/design.md`

---

**维护者**: 团队  
**最后更新**: 2026-02-25
