# Sierac-tm Spec 任务总览（SPEC_TASKS_SCAN）

> **单一真源**：本文件为 Spec 循环与任务扫描的汇总入口  
> **版本**: v3.0.0  
> **最后更新**: 2026-02-28

---

## 功能清单

| Spec | 需求 | 设计 | 任务 | 进度 | 路径 |
|------|------|------|------|------|------|
| **cursor-admin-core** | ✅ | ✅ | ✅ | 已完成（数据底座） | `.kiro/specs/cursor-admin-core/` |
| **cursor-admin-ai-tracking** | ✅ | ✅ | ✅ | **待实施**（P0，核心数据源） | `.kiro/specs/cursor-admin-ai-tracking/` |
| **cursor-admin-projects** | ✅ | ✅ | ✅ | **待重构**（v3.0 轻量立项） | `.kiro/specs/cursor-admin-projects/` |
| **cursor-admin-incentives** | ✅ | ✅ | ✅ | **待重构**（v3.0 简化激励） | `.kiro/specs/cursor-admin-incentives/` |

### 已废弃 Spec（v3.0）

| Spec | 废弃原因 | 路径 |
|------|----------|------|
| ~~cursor-admin-hooks~~ | Hook 整体废弃，官方 API 替代 | `.kiro/specs/_archived/cursor-admin-hooks/` |
| ~~cursor-admin-loop-and-data~~ | Hook 依赖已移除，闭环逻辑不再需要 | `.kiro/specs/_archived/cursor-admin-loop-and-data/` |

---

## 各 Spec 简要

- **cursor-admin-core**：Cursor Admin API 数据同步（成员/用量/支出）、告警规则与通知、管理端查询 API。数据底座，已完成。
- **cursor-admin-ai-tracking**：**Cursor AI Code Tracking API 集成**——commit 级 AI 代码归因数据的自动采集与落库，贡献度量的核心数据源。替代原有的 git_sync.py 和 agent_sessions。
- **cursor-admin-projects**：**轻量立项**——项目 CRUD、关联仓库、预算与激励池设定；通过 repoName 自动归属贡献数据。不做白名单、不做仓库创建。
- **cursor-admin-incentives**：**项目激励**——基于 ai_code_commits 的简单激励计算（激励池 × 贡献占比 × 交付系数）、排行榜、成员端我的贡献。

---

## 执行顺序

```
Phase 1: cursor-admin-ai-tracking（AI Code Tracking API 集成 → 核心数据源）
    ↓
Phase 2: cursor-admin-projects 重构（轻量立项 + 预算 + 激励池）
    ↓
Phase 3: cursor-admin-incentives 重构（简化激励计算 + 排行榜）
    ↓
Phase 4: 废弃代码清理（Hook、git_sync、gitlab_client 等）
```

---

## 检查点（Checkpoint）

| Spec | 最后更新 | 总任务数 | 已完成 | 待完成 |
|------|----------|----------|--------|--------|
| cursor-admin-core | 2026-02-28 | — | 全部 | 0 |
| cursor-admin-ai-tracking | 2026-02-28 | 7 | 0 | 7 |
| cursor-admin-projects | 2026-02-28 | 6 | 0 | 6 |
| cursor-admin-incentives | 2026-02-28 | 7 | 0 | 7 |

---

## v3.0 架构变更摘要

### 新增

- AI Code Tracking API 集成（`ai_code_sync.py`、`ai_code_commits` 表）
- 项目预算与激励池
- 简化激励公式（激励池 × 贡献占比 × 交付系数）

### 废弃

- Hook 整体（Python + Java 客户端、白名单拦截、会话上报）
- `agent_sessions` 表（Hook 上报数据）
- `git_contributions` 表（Git CLI 扫描数据）
- `git_sync.py`（被 `ai_code_sync.py` 替代）
- `gitlab_client.py`（不再需要 GitLab API 集成）
- `hook_templates/` 目录
- 闭环健康/Hook 状态检测

### 保留

- Cursor Admin API 同步（members、daily_usage、spend_snapshots）
- 告警规则与通知
- 管理端 + 成员端框架

---

**维护者**: 团队  
**最后更新**: 2026-02-28
