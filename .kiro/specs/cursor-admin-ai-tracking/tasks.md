# Tasks: AI Code Tracking API 集成

> **状态**：待实施  
> **最后更新**：2026-02-28

---

## 进度概览

- **总任务数**：7
- **已完成**：0
- **待完成**：7

---

## 1. 数据模型与迁移

- [ ] 1.1 新增 `db/migrations/004_ai_code_commits.sql`：创建 `ai_code_commits` 表与索引（幂等）。
- [ ] 1.2 验证迁移：启动 collector 后表自动创建。

---

## 2. API 客户端

- [ ] 2.1 在 `cursor_api.py` 中新增 `get_ai_code_commits()` 方法：
  - 调用 `GET /analytics/ai-code/commits`
  - 支持分页参数（page, pageSize）
  - 支持 ETag 缓存（If-None-Match）
  - 实现 429 退避重试（指数退避，最多 5 次）
  - 单元测试覆盖正常响应、分页、429 重试、304 缓存

---

## 3. 同步任务

- [ ] 3.1 新增 `ai_code_sync.py`：
  - `sync_ai_code_commits()`：增量同步（上次最大 commit_ts → now）
  - 分页遍历所有 commit
  - `match_project()`：repo_name → project_id 匹配
  - 幂等 upsert 到 `ai_code_commits`
  - 错误处理：API 不可达时记录日志，不影响其他任务
- [ ] 3.2 在 `main.py` 注册定时任务（每小时）

---

## 4. 查询 API

- [ ] 4.1 新增查询路由：
  - `GET /api/ai-commits`（管理端，支持筛选与分页）
  - `GET /api/ai-commits/summary`（按项目/成员聚合汇总）
  - `GET /api/ai-commits/my`（成员端，我的 AI 代码贡献）

---

## 5. 验收

- [ ] 5.1 端到端验证：
  - 配置 API Key 后，定时任务拉取数据并落库
  - 管理端可查看按项目的 AI 代码贡献
  - 成员端可查看「我的贡献」
  - commit 数据正确归属到已立项项目

---

## 参考文档

- `.kiro/specs/cursor-admin-ai-tracking/requirements.md`
- `.kiro/specs/cursor-admin-ai-tracking/design.md`
- `docs/ARCHITECTURE.md`

---

**维护者**: 团队  
**最后更新**: 2026-02-28
