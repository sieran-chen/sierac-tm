# Tasks: 项目立项（v3.0 重构）

> **状态**：已完成（v3.0 重构）  
> **最后更新**：2026-03-12

---

## 进度概览

- **总任务数**：6
- **已完成**：6
- **待完成**：0

---

## 1. 数据模型迁移

- [x] 1.1 新增 `007_projects_v3.sql`：为 projects 表添加 budget_amount、budget_period、incentive_pool、incentive_rule_id 字段（ALTER TABLE IF NOT EXISTS，幂等）。
- [x] 1.2 验证迁移兼容性：旧数据不受影响，新字段默认 NULL。

---

## 2. API 重构

- [x] 2.1 更新项目 CRUD API：
  - POST/PUT 支持 budget_amount、budget_period、incentive_pool、incentive_rule_id
  - 移除 workspace_rules、auto_create_repo、reinject-hook 等废弃字段的处理逻辑
- [x] 2.2 更新项目汇总 API：
  - `GET /api/projects/{id}/summary`：budget + ai_code_commits 贡献汇总 + 成员排行（含 contribution_pct）

---

## 3. 前端重构

- [ ] 3.1 更新项目管理页面（前端，待实施）：
  - 新建/编辑表单增加预算和激励池字段
  - 移除白名单规则、GitLab/GitHub 仓库自动创建相关 UI
  - 项目详情页展示预算消耗和 AI 代码贡献

---

## 4. 清理

- [x] 4.1 移除废弃代码（后端）：
  - 白名单查询 API（`/api/projects/whitelist`）已删除
  - reinject-hook API 已删除
  - ProjectCreate/Update 中 workspace_rules、auto_create_repo、repo_slug、repo_provider 已移除
  - GitLab/GitHub 仓库自动创建逻辑已移除

---

## 参考文档

- `.kiro/specs/cursor-admin-projects/requirements.md`
- `.kiro/specs/cursor-admin-projects/design.md`
- `docs/ARCHITECTURE.md`

---

**维护者**: 团队  
**最后更新**: 2026-02-28
