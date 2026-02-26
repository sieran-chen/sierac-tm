# Sierac-tm Spec 任务总览（SPEC_TASKS_SCAN）

> **单一真源**：本文件为 Spec 循环与任务扫描的汇总入口  
> **最后更新**: 2026-02-26

---

## 功能清单

| Spec | 需求 | 设计 | 任务 | 进度 | 路径 |
|------|------|------|------|------|------|
| **cursor-admin-core** | ✅ | ✅ | ✅ | 已完成 | `.kiro/specs/cursor-admin-core/` |
| **cursor-admin-hooks** | ✅ | ✅ | ✅ | Phase 1–2 已完成；Phase 3 Python 已完成，Java 待更新 | `.kiro/specs/cursor-admin-hooks/` |
| **cursor-admin-projects** | ✅ | ✅ | ✅ | **已完成（Phase 0）** | `.kiro/specs/cursor-admin-projects/` |
| **cursor-admin-incentives** | ✅ | ✅ | ✅ | **已完成** | `.kiro/specs/cursor-admin-incentives/` |

---

## 各 Spec 简要

- **cursor-admin-core**：Cursor API 数据同步（成员/用量/支出）、Hook 会话接收（含 project_id）、告警规则与通知、管理端查询 API。数据底座，已完成。
- **cursor-admin-hooks**：Hook 协议（beforeSubmitPrompt 白名单校验 + stop 会话上报）、上报契约（POST /api/sessions，含 project_id）；Java 与 Python 双实现；项目级自动部署（`.cursor/` 目录注入）。
- **cursor-admin-projects**：**项目立项与治理**——项目 CRUD、白名单管理、Hook 准入拦截、会话归属项目、Git 仓库采集、按项目聚合成本与贡献；**GitLab 与 GitHub** 仓库自动创建与 Hook 注入。Phase 0，所有贡献可视化与激励的前置。
- **cursor-admin-incentives**：贡献度计算（三源融合：Git + Hook + Cursor API）、个人贡献画像、排行榜、激励规则配置。依赖 projects spec 提供的项目实体与 Git 贡献数据。

---

## 执行顺序

```
Phase 0: cursor-admin-projects（立项 → 白名单 → Git 采集 → 按项目聚合 → GitLab/GitHub 自动化）
    ↓
Phase 1: cursor-admin-incentives Phase 1（贡献度计算 + 我的贡献）
    ↓
Phase 2: cursor-admin-incentives Phase 2（排行榜 + 激励闭环）
```

---

## 检查点（Checkpoint）

| Spec | 最后更新 | 总任务数 | 已完成 | 进行中 | 待完成 | 阻塞 |
|------|----------|----------|--------|--------|--------|------|
| cursor-admin-core | 2026-02-26 | — | 全部 | — | — | — |
| cursor-admin-hooks | 2026-02-26 | 13 | 11 | 0 | 2（Java 白名单） | 无 |
| cursor-admin-projects | 2026-02-26 | 27 | 27（全部完成） | 0 | 0 | 无 |
| cursor-admin-incentives | 2026-02-26 | 15 | 15（全部完成） | 0 | 0 | 无 |

### cursor-admin-projects 当前进度明细

**已完成**：
- Phase -1（遗留清理）：C1–C5 全部完成
- Phase 0-A（数据模型与 CRUD）：Task 1–6 已完成（迁移、CRUD API、白名单、管理端页面、API client、导航）
- Phase 0-B（Hook 白名单校验）：Task 7、8、9、10 已完成（Python 实现 + 服务端补填）
- Phase 0-C：Task 12–14 已完成（contributions/summary API、项目详情页）
- Phase 0-D：Task 15（/api/contributions/my）、Task 16（我的项目视图）已完成
- Phase 0-E：Task 17（工作目录页改造为按项目聚合）、Task 19–27 已完成（含 E2E 验证清单 `E2E_VERIFICATION.md`）
- Task 11（Git 采集定时任务）、Task 18（E2E 验证清单扩展）已完成

**cursor-admin-projects 已全部完成。**

**cursor-admin-incentives**：已全部完成（Task 1–15，含成员端我的贡献页、E2E 验证清单、ARCHITECTURE §5.5）。

---

**维护者**: 团队  
**最后更新**: 2026-02-26
