# Tasks: 业务闭环与数据可见性

> **状态**：待执行  
> **依赖**：cursor-admin-core、cursor-admin-projects、cursor-admin-incentives

---

## 1. 闭环健康 / Hook 状态 API

- [x] **Task 1**：Collector 新增 `GET /api/health/loop`（或 `GET /api/hook-status`），鉴权同现有 x-api-key；查询最近 7 天内 `agent_sessions` 的 COUNT、MAX(ended_at)、COUNT(DISTINCT user_email)；返回 JSON：`loop_ok`、`days_checked`、`last_session_at`、`sessions_count_7d`、`members_with_sessions_7d`。实现位置：`collector/main.py`。
- [x] **Task 2**：前端 api client 新增 `loopHealth()` 或 `hookStatus()` 调用上述接口；类型定义与 `docs/BUSINESS_LOOP_AND_HOOK.md` 中描述一致。

---

## 2. 数据可见性文档与排查清单

- [x] **Task 3**：新增 `docs/DATA_VISIBILITY_AND_TROUBLESHOOTING.md`，包含：  
  - 用量、支出、Git 贡献、Hook 四类数据的「可展示条件」与「不展示时排查清单」（与 design §2、§3 一致）。  
  - 闭环可验证性的含义及 GET /api/health/loop 的用途与示例。  
  - 指向 Hook 安装与验证文档的链接（如有）。
- [x] **Task 4**：在 `docs/ARCHITECTURE.md` 或文档引用表中增加《数据可见性条件与排查》的引用。

---

## 3. 管理端：闭环健康展示与无 Hook 引导

- [x] **Task 5**：管理端增加「闭环健康」或「Hook 状态」的展示入口：  
  - 方案 A：在「项目参与」页顶部增加卡片/横幅，调用 GET /api/health/loop；当 `loop_ok === false` 时展示「尚未检测到 Hook 上报，接通后可查看项目参与与激励」及《数据可见性条件与排查》或 Hook 安装文档链接。  
  - 方案 B：在 Layout 或仪表盘（若有）增加轻量横幅，逻辑同上。  
  - 实现位置：`cursor-admin/web/src/`，新组件或已有页内区块均可。
- [ ] **Task 6**：依赖 Hook 的页面（项目参与、排行榜、我的贡献）在空状态文案中可增加「接通 Hook 后可查看」的短句及指向同一文档的链接（若尚未存在）。

---

## 4. 支出管理 / Git 贡献空状态与错误说明

- [ ] **Task 7**：支出管理页：当请求失败或返回空列表时，展示与「可展示条件」一致的说明（如「请检查 Cursor API 配置与同步任务」「暂无支出数据，可能当前套餐未提供或同步尚未完成」）；与 design §2.4 一致。
- [ ] **Task 8**：项目详情「Git 贡献」、我的项目等已有空状态文案；确认包含「配置关联仓库」「采集服务执行 Git 采集」等要点，并可选增加《数据可见性条件与排查》链接。

---

## 5. 验收与收口

- [x] **Task 9**：API GET /api/health/loop 可通过 curl 或前端调用返回预期 JSON；当 agent_sessions 无数据时 `loop_ok` 为 false。
- [x] **Task 10**：管理端在「闭环未通」时可见引导入口；文档 `docs/DATA_VISIBILITY_AND_TROUBLESHOOTING.md` 存在且包含四类数据与排查清单。

---

**维护者**：团队  
**最后更新**：2026-02-26
