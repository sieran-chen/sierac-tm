# Sierac-tm Spec 任务总览（SPEC_TASKS_SCAN）

> **单一真源**：本文件为 Spec 循环与任务扫描的汇总入口  
> **最后更新**: 2026-02-25

---

## 功能清单

| Spec | 需求 | 设计 | 任务 | 进度 | 路径 |
|------|------|------|------|------|------|
| **cursor-admin-core** | ✅ | ✅ | ✅ | 见 tasks | `.kiro/specs/cursor-admin-core/` |
| **cursor-admin-hooks** | ✅ | ✅ | ✅ | 见 tasks | `.kiro/specs/cursor-admin-hooks/` |
| **cursor-admin-incentives** | ✅ | ✅ | ✅ | 预留 | `.kiro/specs/cursor-admin-incentives/` |

---

## 各 Spec 简要

- **cursor-admin-core**：用量统计、支出管理、告警规则与历史、工作目录/会话汇总；数据同步与持久化；管理端 API 与页面。
- **cursor-admin-hooks**：Hook 协议（beforeSubmitPrompt / stop）、上报契约（POST /api/sessions）；Java 与 Python 双实现；安装与分发。
- **cursor-admin-incentives**：预留扩展；贡献度指标、排行、评分规则；与激励管理挂钩的架构预留。

---

## 检查点（Checkpoint）

扫描时依据各 spec 的 `tasks.md` 中勾选统计进度；本文件不重复维护具体数字，以各 `tasks.md` 为准。

---

**维护者**: 团队  
**最后更新**: 2026-02-25
