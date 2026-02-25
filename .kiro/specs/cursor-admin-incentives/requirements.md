# Requirements: Cursor Admin 团队激励（预留）

> **目标**：将本系统扩展为团队激励管理工具，支持贡献度排行、评分，与激励挂钩。  
> **优先级**：P2（预留，后续迭代）  
> **预估工作量**：10–15 天（启动时）

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-incentives/requirements.md`
- design: `.kiro/specs/cursor-admin-incentives/design.md`
- tasks: `.kiro/specs/cursor-admin-incentives/tasks.md`

---

## 1. 背景与动机

- 在用量与工作目录可见性基础上，希望与**团队激励**结合：贡献度排行、评分、与绩效或奖励挂钩。
- 数据来源保持粗颗粒度（daily_usage、agent_sessions、spend），不引入细粒度 Hook。

---

## 2. 用户故事（预留）

### 2.1 作为管理员

**故事**：查看按周期（周/月）的成员贡献度排行与得分，并支持配置评分规则（权重、维度）。

**验收标准**（待细化）：
- [ ] 支持多维度得分：如 Agent 使用量、会话时长、工作目录深度、代码行贡献等。
- [ ] 支持可配置权重与周期；排行可按时段快照留存。
- [ ] 数据来源于现有 daily_usage、agent_sessions、spend，不新增 Hook。

### 2.2 作为成员

**故事**：查看自己的得分与在团队中的相对排名（若开放）。

**验收标准**（待细化）：
- [ ] 提供「我的得分」「我的排名」视图；权限由管理员控制。

---

## 3. 功能需求（预留）

- **FR-1**：贡献度指标定义（基于现有表的聚合：如 agent_requests、duration_seconds、total_lines_added 等）。
- **FR-2**：评分规则配置（权重、周期、维度）；规则存储与版本管理。
- **FR-3**：定期计算得分并写入 contribution_scores 或等价表；可选 leaderboard_snapshots。
- **FR-4**：管理端与成员端 API/页面：排行、得分、历史快照。

具体字段与接口在启动本 spec 时于 design.md 中补全。

---

## 4. 约束与假设

- 仅使用已采集的粗颗粒度数据；不新增 Cursor Hook 事件。
- 与 cursor-admin-core 共享 DB；扩展表需在 design 中定义并提供迁移。

---

## 5. 依赖

- **内部**：cursor-admin-core（sync 与表结构）；若需扩展表与任务，在 design/tasks 中明确。

---

## 6. 参考文档

- `docs/ARCHITECTURE.md` §5（扩展：团队激励管理）
- `.kiro/specs/cursor-admin-core/`

---

**维护者**: 团队  
**最后更新**: 2026-02-25  
**状态**: 预留，未启动实现
