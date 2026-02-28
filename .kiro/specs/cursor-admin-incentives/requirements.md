# Requirements: 项目激励

> **目标**：基于 AI Code Tracking 数据，实现简单透明的项目激励计算与分配，推动团队 AI 转型。  
> **优先级**：P1（依赖 cursor-admin-ai-tracking 和 cursor-admin-projects 完成）  
> **预估工作量**：5–8 天

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-incentives/requirements.md`
- design: `.kiro/specs/cursor-admin-incentives/design.md`
- tasks: `.kiro/specs/cursor-admin-incentives/tasks.md`

---

## 1. 背景与动机

- AI Code Tracking API 提供了精确的 commit 级 AI 代码归因数据。
- 项目立项时设定了预算和激励池。
- 需要将 AI 代码贡献转化为激励分配，形成「贡献可见 → 激励分配 → 主动参与」的闭环。
- 激励规则必须简单透明，每个人都能算出自己的份额。

### 与旧设计的区别

| 维度 | 旧设计（v2） | 新设计（v3） |
|------|-------------|-------------|
| 数据来源 | Git + Hook + Cursor API（三源融合） | AI Code Tracking API（单一权威源） |
| Hook 依赖 | 仅 Hook 用户参与排行 | 无 Hook，全员自动参与 |
| 激励规则 | 多维度权重（5+ 维度） | 简单公式：激励池 × 贡献占比 × 交付系数 |
| 参与门槛 | 需安装 Hook | 无门槛，有 commit 即参与 |

---

## 2. 用户故事

### 2.1 作为管理员

**故事**：配置激励规则，查看按周期的激励分配结果和排行榜。

**验收标准**：
- [ ] 管理端有「激励规则」页面，支持配置周期和交付系数。
- [ ] 管理端有「排行榜」页面，展示按周期的成员贡献排行和激励分配。
- [ ] 支持导出 CSV。
- [ ] 每个周期自动生成激励快照。

### 2.2 作为成员

**故事**：查看自己的 AI 代码贡献得分、在团队中的排名、以及激励份额。

**验收标准**：
- [ ] 成员端「我的贡献」展示：本周期得分、排名、激励份额预估。
- [ ] 展示历史趋势（近 8 周/月）。
- [ ] 展示按项目的贡献分布。

---

## 3. 功能需求

### FR-1：激励规则

- 规则存储于 `incentive_rules` 表。
- 核心字段：周期类型（weekly/monthly）、交付系数说明。
- 规则简单：**激励池 × 成员贡献占比 × 交付系数**。
- 贡献占比 = 成员在该项目的 AI 代码行数 / 项目全部 AI 代码行数。
- 交付系数由管理员手动设定（按时交付 1.0，延期递减）。

### FR-2：贡献度计算

- 定时任务按周期（每日/每周/每月）计算。
- 数据来源：`ai_code_commits` 表（按 project_id + user_email + 周期聚合）。
- 写入 `contribution_scores` 表。
- 计算排名。

### FR-3：激励分配

- 按项目计算：项目激励池 × 成员贡献占比 × 交付系数 = 成员激励金额。
- 跨项目汇总：成员在所有项目的激励总额。
- 写入 `contribution_scores` 的 `incentive_amount` 字段。

### FR-4：排行榜

- 按周期展示成员排行（总 AI 代码贡献、激励金额）。
- 支持按项目筛选。
- 排行快照写入 `leaderboard_snapshots`。

### FR-5：成员端 API

- `GET /api/contributions/my`：我的贡献得分、排名、激励份额、趋势。
- `GET /api/contributions/leaderboard`：排行榜。

---

## 4. 非功能需求

- **透明**：每个成员能看到自己的计算过程（AI 行数、占比、激励池、系数、最终金额）。
- **可审计**：每个周期的排行快照留存。
- **简单**：规则不超过 3 个参数（激励池、贡献占比、交付系数）。

---

## 5. 约束与假设

- 贡献数据完全来自 `ai_code_commits`，不再依赖 Hook 或 Git CLI 扫描。
- 全员自动参与，无需安装任何客户端。
- 交付系数由管理员手动设定，未来可接入项目管理工具自动化。

---

## 6. 依赖

- **内部**：cursor-admin-ai-tracking（ai_code_commits 数据）；cursor-admin-projects（projects 表、预算、激励池）。

---

**维护者**: 团队  
**最后更新**: 2026-02-28  
**状态**: 待重构
