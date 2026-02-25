# Worktree 任务分配（Sierac-tm）

> **角色**: 多 Worktree 并行开发时的任务分配真源（可选）  
> **更新者**: 人工（或 Cursor 辅助）  
> **最后更新**: 2026-02-25

---

## 规则

1. **AI Agent 启动时可读取本文件**，确认当前 worktree 的任务分配。
2. **只做分配给自己的 spec/模块**，不越界。
3. **任务分配由人工更新**，AI 不得自行修改本文件。
4. 单 worktree 开发时可忽略本文件；多 worktree 时再启用分配表。

---

## 当前分配（单 worktree 默认）

| 目录 | 分支 | 角色 | 当前 spec |
|------|------|------|-----------|
| 本仓库 | main | 统筹 + 编码 | cursor-admin-core / hooks / incentives（按 SPEC_TASKS_SCAN 推进） |

---

## 跨 Spec 依赖提示

| 源 Spec | 影响 Spec | 影响内容 |
|---------|-----------|----------|
| cursor-admin-hooks | cursor-admin-core | Hook 上报协议与 collector `/api/sessions` 契约一致 |
| cursor-admin-incentives | cursor-admin-core | 依赖 daily_usage、agent_sessions、spend 表与 sync 数据 |

---

**说明**：本项目当前按单 worktree 使用；若后续引入多 worktree，在此补充分配表即可。
