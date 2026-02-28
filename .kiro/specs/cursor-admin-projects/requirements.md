# Requirements: 项目立项

> **目标**：以「项目」为一等实体，实现轻量立项（登记项目、关联仓库、设定预算与激励池），为贡献归属和激励分配提供基础。  
> **优先级**：P0  
> **预估工作量**：3–5 天（在现有基础上重构）

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-projects/requirements.md`
- design: `.kiro/specs/cursor-admin-projects/design.md`
- tasks: `.kiro/specs/cursor-admin-projects/tasks.md`

---

## 1. 背景与动机

- 项目是平台的一等实体，所有贡献数据、预算、激励都围绕项目组织。
- 立项 = 在平台上登记项目信息，不自动创建仓库、不注入 Hook、不做白名单拦截。
- AI Code Tracking API 返回 `repoName`，系统通过匹配 `projects.git_repos` 自动归属贡献数据。

### 与旧设计的区别

| 维度 | 旧设计（v2） | 新设计（v3） |
|------|-------------|-------------|
| 立项动作 | 自动创建 GitLab 仓库 + 注入 Hook | 登记项目信息，手动填写仓库地址 |
| 准入控制 | Hook 白名单拦截 | 无（管理手段解决） |
| 数据归属 | Hook workspace_roots 匹配 | API repoName 匹配 git_repos |
| 预算 | 无 | 项目预算 + 激励池 |

---

## 2. 用户故事

### 2.1 作为管理员——立项

**故事**：我要在平台登记一个公司项目，填写项目名称、关联仓库地址、参与成员、预算和激励池。

**验收标准**：
- [ ] 管理端有「项目管理」页面，支持新建/编辑/归档项目。
- [ ] 项目信息包含：名称、描述、Git 仓库地址（可多个）、参与成员（可选）、状态、预算额度、预算周期、激励池。
- [ ] 立项后系统自动将 AI Code Tracking 数据归属到该项目（通过 repoName 匹配）。

### 2.2 作为管理员——按项目看预算与贡献

**故事**：我要按项目查看预算消耗和 AI 代码贡献，评估投入产出。

**验收标准**：
- [ ] 项目详情页展示：预算消耗（基于 spend 数据）、AI 代码贡献汇总（基于 ai_code_commits）。
- [ ] 支持按时间范围筛选。

### 2.3 作为成员——看到自己参与的项目

**故事**：我要看到自己参与了哪些项目，以及在每个项目上的 AI 代码贡献。

**验收标准**：
- [ ] 成员端有「我的项目」视图，展示我有 commit 的项目列表及贡献摘要。

---

## 3. 功能需求

### FR-1：项目 CRUD

- 管理端页面 + Collector API（`/api/projects`）。
- 字段：name, description, git_repos (text[]), member_emails (text[]), status, budget_amount, budget_period, incentive_pool, incentive_rule_id, created_by, created_at, updated_at。
- 支持 active / archived 状态切换。

### FR-2：数据归属

- AI Code Tracking 同步时，通过 `repoName` 匹配 `projects.git_repos` 写入 `project_id`。
- 匹配逻辑在 `ai_code_sync.py` 中实现（见 cursor-admin-ai-tracking spec）。

### FR-3：项目详情 API

- `GET /api/projects/{id}/summary`：预算消耗、AI 代码贡献汇总、参与成员数。
- `GET /api/projects/{id}/members`：该项目有 commit 的成员列表及贡献。

### FR-4：管理端页面

- 项目列表页（ProjectsPage）：项目卡片，显示名称、状态、预算、AI 代码总量。
- 项目详情页（ProjectDetailPage）：预算消耗、成员贡献排行、AI 代码趋势。

---

## 4. 非功能需求

- **兼容**：现有 projects 表需迁移增加 budget/incentive 字段。
- **性能**：项目列表查询 < 200ms。

---

## 5. 约束与假设

- 仓库地址由管理员手动填写，格式可能不统一（HTTPS/SSH/短名），匹配逻辑需容错。
- 预算追踪基于 spend_snapshots 按成员聚合，再通过成员与项目的关联估算项目支出。

---

## 6. 依赖

- **内部**：cursor-admin-core（DB、Collector 框架）；cursor-admin-ai-tracking（ai_code_commits 数据）。

---

**维护者**: 团队  
**最后更新**: 2026-02-28  
**状态**: 待重构
