# Design: 业务闭环与数据可见性

> **目标**：给出用量、支出、Git 贡献、Hook 四类数据的流与前置条件，闭环健康/Hook 状态 API 与无 Hook 时 UI 策略的技术设计，以及「不展示」时的排查清单。  
> **状态**：与 requirements 配套

---

## 文档联动

- requirements: `.kiro/specs/cursor-admin-loop-and-data/requirements.md`
- design: `.kiro/specs/cursor-admin-loop-and-data/design.md`
- tasks: `.kiro/specs/cursor-admin-loop-and-data/tasks.md`

---

## 1. 数据流与前置条件总览

| 数据 | 来源 | 写入表 | 同步触发 | 可展示前提 |
|------|------|--------|----------|------------|
| 用量 | Cursor API `get_daily_usage` | `daily_usage` | run_full_sync（定时，默认 60 分钟） | CURSOR_API_TOKEN 已配置；sync 已成功跑过 |
| 支出 | Cursor API `get_spend` | `spend_snapshots` | 同上 | 同上；且 Cursor 套餐返回 teamMemberSpend |
| Git 贡献 | git clone/fetch + git log | `git_contributions` | run_git_collect（在 sync 之后同周期） | 项目 git_repos 非空；GIT_REPOS_ROOT 可写；环境有 git；仓库可访问 |
| Hook 会话 | POST /api/sessions | `agent_sessions` | 实时 | 成员在匹配目录装 Hook；白名单可访问；beforeSubmitPrompt 匹配成功 |

---

## 2. 支出不展示：原因与排查

### 2.1 数据流

```
Cursor API POST /teams/spend
  → sync_spend() 解析 data.teamMemberSpend、data.subscriptionCycleStart
  → INSERT INTO spend_snapshots (email, billing_cycle_start, spend_cents, ...)
  → GET /api/usage/spend 读 spend_snapshots 与 members 关联
```

### 2.2 不展示的常见原因

1. **CURSOR_API_TOKEN 未配置或无效**：sync 报错，spend_snapshots 无数据。
2. **同步未执行或失败**：例如 collector 刚启动未到整点、sync_spend 抛异常被 catch 仅打日志。
3. **Cursor API 未返回支出**：部分团队套餐可能无 `/teams/spend` 或返回空 `teamMemberSpend`。
4. **表不存在或迁移未跑**：spend_snapshots 在 001_init.sql 中创建，若迁移未执行则查询报错。

### 2.3 排查清单（可执行）

- [ ] 环境变量：`CURSOR_API_TOKEN` 已配置且非空。
- [ ] 日志：collector 日志中是否有 `sync_spend failed` 或 401/5xx。
- [ ] 直接调 Cursor API：用同 token 请求 `POST {CURSOR_API_URL}/teams/spend`，看是否返回 `teamMemberSpend` 数组。
- [ ] 数据库：`SELECT COUNT(*) FROM spend_snapshots;` 是否有行；若有，前端是否用对 API（/api/usage/spend）与 x-api-key。

### 2.4 前端/产品

- 支出管理页：加载失败时展示「请检查 Cursor API 配置与同步任务」；空表时展示「暂无支出数据，可能当前套餐未提供或同步尚未完成」。
- 可选：管理端「系统状态」或设置页展示「最近一次同步时间」或「支出数据最后更新」（max(synced_at) from spend_snapshots）。

---

## 3. Git 贡献不展示：原因与排查

### 3.1 数据流

```
projects 表 (status='active' AND git_repos 非空)
  → run_git_collect() 每项目每 repo_url
  → clone --bare <repo_url> 或 fetch（存于 GIT_REPOS_ROOT/{project_id}/{hash}/）
  → git log --since=... + git show --numstat → 解析 author_email, commit_date, 增删行
  → INSERT INTO git_contributions ON CONFLICT DO UPDATE
  → 项目详情/我的项目/我的贡献 读 git_contributions
```

### 3.2 不展示的常见原因

1. **项目未配置关联仓库**：`git_repos` 为空或 NULL，run_git_collect 不处理该项目。
2. **GIT_REPOS_ROOT 未配置或不可写**：默认 `/data/git-repos`；Docker 需挂载卷或目录可写。
3. **环境无 git**：Collector 镜像或运行环境未安装 git，clone/fetch 失败。
4. **clone/fetch 失败**：私有仓库无凭证、网络不可达、URL 错误（如少 .git 或协议错误）。
5. **同步周期未到**：run_git_collect 在 run_full_sync 之后执行，若 sync 刚跑完第一次，需等下一轮或重启触发。

### 3.3 排查清单（可执行）

- [ ] 项目配置：`SELECT id, name, git_repos FROM projects WHERE status='active';`，目标项目 `git_repos` 非空且 URL 正确。
- [ ] 环境变量：`GIT_REPOS_ROOT`（默认 /data/git-repos）、`GIT_COLLECT_DAYS`；Docker 挂载 `git_repos_data:/data/git-repos`。
- [ ] 环境：容器内执行 `git --version` 存在。
- [ ] 日志：collector 日志中 `git_collector` 是否有 `clone failed` / `fetch failed` / `git log failed`。
- [ ] 数据库：`SELECT COUNT(*) FROM git_contributions WHERE project_id=?;` 是否有行（对应项目 id）。

### 3.4 前端/产品

- 项目详情「Git 贡献」空时：已有一句「请确保项目已填写关联仓库且采集服务已配置 GIT_REPOS_ROOT…」；可补充「排查见《数据可见性条件与排查》」链接。
- 我的项目空时：已说明「请确保项目已配置关联仓库且采集服务已执行 Git 采集」；同上可链到文档。

---

## 4. 闭环健康 / Hook 状态 API

### 4.1 判定定义

- **全局「闭环已接通」**：最近 N 天（如 7 天）内存在至少一条 `agent_sessions` 记录。
- **可选**：最近 N 天内存在至少一条 `project_id IS NOT NULL` 的会话（表示不仅上报了，还归属到项目）。

### 4.2 接口设计

- **GET /api/health/loop**（或 **GET /api/hook-status**）  
  - 鉴权：与现有管理端 API 一致（x-api-key）。  
  - 响应示例：
    ```json
    {
      "loop_ok": true,
      "days_checked": 7,
      "last_session_at": "2026-02-26T10:00:00Z",
      "sessions_count_7d": 42,
      "members_with_sessions_7d": 3
    }
    ```
  - 当 7 天内无任何 agent_sessions 时：`loop_ok: false`，`last_session_at` 可为 null，`sessions_count_7d: 0`。

### 4.3 实现要点

- 查询：`SELECT COUNT(*), MAX(ended_at) FROM agent_sessions WHERE ended_at >= NOW() - INTERVAL '7 days'`；可选 `SELECT COUNT(DISTINCT user_email) ...`。
- 不依赖 contribution_scores；仅读 agent_sessions，表在 002 中已有。

---

## 5. 无 Hook 时的产品形态（UI 策略）

### 5.1 策略选择

- **推荐**：不隐藏「项目参与」「排行榜」「我的贡献」入口，保留空状态与引导；在**仪表盘或项目参与页顶部**增加一块「闭环健康」卡片或横幅：若 `loop_ok === false`，展示「尚未检测到 Hook 上报，接通后可查看项目参与与激励」+ 链接到《Hook 安装与验证》或帮助页。
- **可选**：若产品决策为「闭环未通时弱化依赖 Hook 的入口」，可在导航中对该几项加「即将开通」角标或收起到「更多」中，但需在 design 中明确并写入 tasks。

### 5.2 前端数据依赖

- 管理端需调用 GET /api/health/loop（或 /api/hook-status）以决定是否展示「闭环未通」引导。
- 展示位置：仪表盘（若有）或「项目参与」页顶部；或 Layout 内一条轻量横幅。

### 5.3 引导文案与文档

- 统一引导入口指向《Hook 安装与验证》或《数据可见性条件与排查》文档。
- 依赖 Hook 的页面空状态中可缩短为「接通 Hook 后可查看本页数据」，并链到同一文档。

---

## 6. 文档产出

- **《数据可见性条件与排查》**（建议放在 `docs/DATA_VISIBILITY_AND_TROUBLESHOOTING.md`）：  
  - 用量、支出、Git 贡献、Hook 四类数据的「可展示条件」与「不展示时排查清单」（与 §2、§3 一致）。  
  - 闭环可验证性的含义与 GET /api/health/loop 的用法。  
- 现有 `docs/BUSINESS_LOOP_AND_HOOK.md` 可保留并引用本 spec 与上述文档。

---

## 7. 依赖与约束

- 依赖 cursor-admin-core（agent_sessions、spend_snapshots、daily_usage、members）、cursor-admin-projects（projects、git_contributions）、现有 sync 与 git_collector。
- 不改变现有 sync/git_collect 触发时机；仅增加查询接口与前端展示、文档与排查清单。

---

**维护者**：团队  
**最后更新**：2026-02-26
