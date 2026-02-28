# Tasks: 项目立项（v3.0 重构）

> **状态**：待重构  
> **最后更新**：2026-02-28

---

## 进度概览

- **总任务数**：6
- **已完成**：0（v3.0 重构，旧任务已归档）
- **待完成**：6

---

## 1. 数据模型迁移

- [ ] 1.1 新增 `005_projects_v3.sql`：为 projects 表添加 budget_amount、budget_period、incentive_pool、incentive_rule_id 字段。
- [ ] 1.2 验证迁移兼容性：旧数据不受影响，新字段默认 NULL。

---

## 2. API 重构

- [ ] 2.1 更新项目 CRUD API：
  - POST/PUT 支持 budget_amount、budget_period、incentive_pool、incentive_rule_id
  - 移除 workspace_rules、gitlab_project_id 等废弃字段的处理逻辑
- [ ] 2.2 新增/更新项目汇总 API：
  - `GET /api/projects/{id}/summary`：预算消耗 + AI 代码贡献汇总
  - `GET /api/projects/{id}/members`：成员贡献排行

---

## 3. 前端重构

- [ ] 3.1 更新项目管理页面：
  - 新建/编辑表单增加预算和激励池字段
  - 移除白名单规则、GitLab 仓库创建相关 UI
  - 项目详情页展示预算消耗和 AI 代码贡献

---

## 4. 清理

- [ ] 4.1 移除废弃代码：
  - 白名单查询 API（`/api/projects/whitelist`）
  - GitLab 仓库创建逻辑
  - Hook 模板注入逻辑
  - workspace_rules 相关匹配逻辑

---

## 参考文档

- `.kiro/specs/cursor-admin-projects/requirements.md`
- `.kiro/specs/cursor-admin-projects/design.md`
- `docs/ARCHITECTURE.md`

---

**维护者**: 团队  
**最后更新**: 2026-02-28
