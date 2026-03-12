# Tasks: 项目激励（v3.0 重构）

> **状态**：已完成（v3.0 重构）  
> **最后更新**：2026-03-12

---

## 进度概览

- **总任务数**：7
- **已完成**：6（1.1/2.1/2.2/3.1/5.1 后端；4.1–4.3 前端待更新）
- **待完成**：1（4.1–4.3 前端页面更新）

---

## 1. 数据模型

- [x] 1.1 新增 `008_incentives_v3.sql`：contribution_scores 新增 ai_lines_added、total_lines_added、ai_ratio、contribution_pct、delivery_factor、incentive_amount 字段（幂等 ALTER TABLE）。

---

## 2. 计算引擎

- [x] 2.1 重写 `contribution_engine.py`：
  - 数据来源改为 `ai_code_commits`（tab_lines_added + composer_lines_added = ai_lines）
  - 计算公式：incentive_pool × contribution_pct × delivery_factor
  - 移除 Hook 相关逻辑（hook_adopted、session_duration、git_contributions、agent_sessions）
- [x] 2.2 定时任务已注册（每周一 01:00、每月 1 日 01:30，Asia/Shanghai）

---

## 3. API

- [x] 3.1 更新 API 路由：
  - `GET /api/contributions/my`：改为读 contribution_scores 的 ai_lines_added/incentive_amount
  - `GET /api/contributions/leaderboard`：移除 hook_only 参数，按 ai_lines_added 排序
  - 激励规则 CRUD 保留，手动重新计算端点保留

---

## 4. 前端

- [ ] 4.1 更新排行榜页：移除 Hook 状态列，新增激励金额列
- [ ] 4.2 更新我的贡献页：移除 Hook 引导，展示激励份额
- [ ] 4.3 更新激励规则页：简化为周期 + 交付系数配置

---

## 5. 清理

- [x] 5.1 移除废弃代码（后端）：
  - contribution_engine.py 中 hook_adopted、session_duration_hours、agent_sessions、git_contributions 全部移除
  - leaderboard API 移除 hook_only 参数
  - my_contributions API 移除 hook_adopted、score_breakdown 旧字段

---

## 参考文档

- `.kiro/specs/cursor-admin-incentives/requirements.md`
- `.kiro/specs/cursor-admin-incentives/design.md`
- `docs/ARCHITECTURE.md`

---

**维护者**: 团队  
**最后更新**: 2026-02-28
