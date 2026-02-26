# Tasks: 贡献可视化与团队激励

> **状态**：实施中（Phase 1 进行中）  
> **最后更新**：2026-02-26

---

## 进度概览

- **总任务数**：15
- **已完成**：4（Task 1–4）
- **进行中**：0
- **未开始**：11

---

## Phase 1：数据模型与计算引擎

- [x] **Task 1**：创建 `003_incentives.sql` 迁移文件（incentive_rules、contribution_scores、leaderboard_snapshots 表；默认规则初始数据）
- [x] **Task 2**：实现 `collector/contribution_engine.py`：三源数据聚合 + 权重计算 + 排名更新
- [x] **Task 3**：Collector 定时任务：每日/每周/每月触发贡献度计算（APScheduler）
- [x] **Task 4**：单元测试：contribution_engine 计算逻辑（mock DB，覆盖 hook_adopted/未接入/数据缺失场景）

---

## Phase 2：API

- [ ] **Task 5**：Collector 新增 `GET /api/contributions/my`（成员端：我的贡献，含得分、排名、维度明细、项目分布）
- [ ] **Task 6**：Collector 新增 `GET /api/contributions/leaderboard`（管理端：排行榜，支持 hook_only 过滤）
- [ ] **Task 7**：Collector 新增 `GET/POST/PUT/DELETE /api/incentive-rules`（规则 CRUD）
- [ ] **Task 8**：Collector 新增 `POST /api/incentive-rules/{id}/recalculate`（手动触发重新计算）

---

## Phase 3：管理端页面

- [ ] **Task 9**：管理端新增「排行榜」页面（周期选择、排行表、Hook 状态过滤、CSV 导出）
- [ ] **Task 10**：管理端新增「规则配置」页面（权重可视化、滑块编辑、上限配置、重新计算按钮）
- [ ] **Task 11**：管理端 API client 新增 contributions、incentive-rules 相关类型与方法

---

## Phase 4：成员端页面

- [ ] **Task 12**：成员端新增「我的贡献」页面（得分卡、历史趋势、项目分布、Hook 状态提示）
- [ ] **Task 13**：成员端导航新增「我的贡献」入口

---

## Phase 5：验收与收尾

- [ ] **Task 14**：端到端验证：立项 → Git commit → Hook 上报 → 计算触发 → 排行榜展示
- [ ] **Task 15**：文档更新：ARCHITECTURE.md §5 补全激励模块实现细节

---

## 验收清单

- [ ] 贡献度计算覆盖三源数据（git_contributions、agent_sessions、daily_usage）
- [ ] 未装 Hook 的成员不参与排行（hook_adopted=false）
- [ ] 权重可配置，修改后可手动重新计算
- [ ] 管理端排行榜正确展示，支持 Hook 过滤
- [ ] 成员端「我的贡献」展示个人得分与历史趋势
- [ ] 历史快照留存，排行可审计

---

## 依赖与阻塞

- **阻塞**：cursor-admin-projects 全部完成（需要 projects 表、git_contributions 表、agent_sessions.project_id）
- **内部依赖**：cursor-admin-core（DB 连接、Collector 框架）

---

**维护者**: 团队  
**最后更新**: 2026-02-26
