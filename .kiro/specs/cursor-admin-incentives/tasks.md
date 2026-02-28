# Tasks: 项目激励（v3.0 重构）

> **状态**：待重构  
> **最后更新**：2026-02-28

---

## 进度概览

- **总任务数**：7
- **已完成**：0（v3.0 重构，旧任务已归档）
- **待完成**：7

---

## 1. 数据模型

- [ ] 1.1 更新/新增迁移文件：简化 incentive_rules 和 contribution_scores 表结构，新增 incentive_amount、delivery_factor 字段。

---

## 2. 计算引擎

- [ ] 2.1 重写 `contribution_engine.py`：
  - 数据来源改为 `ai_code_commits`（替代三源融合）
  - 计算公式：激励池 × 贡献占比 × 交付系数
  - 移除 Hook 相关逻辑（hook_adopted、session_duration 等）
- [ ] 2.2 注册定时任务（每周一、每月 1 日）

---

## 3. API

- [ ] 3.1 更新 API 路由：
  - `GET /api/contributions/my`：基于 ai_code_commits 聚合
  - `GET /api/contributions/leaderboard`：移除 hook_only 过滤
  - 激励规则 CRUD（简化字段）
  - 手动重新计算

---

## 4. 前端

- [ ] 4.1 更新排行榜页：移除 Hook 状态列，新增激励金额列
- [ ] 4.2 更新我的贡献页：移除 Hook 引导，展示激励份额
- [ ] 4.3 更新激励规则页：简化为周期 + 交付系数配置

---

## 5. 清理

- [ ] 5.1 移除废弃代码：
  - hook_adopted 相关逻辑
  - session_duration_hours 维度
  - agent_sessions 聚合逻辑
  - 多维度权重配置 UI

---

## 参考文档

- `.kiro/specs/cursor-admin-incentives/requirements.md`
- `.kiro/specs/cursor-admin-incentives/design.md`
- `docs/ARCHITECTURE.md`

---

**维护者**: 团队  
**最后更新**: 2026-02-28
