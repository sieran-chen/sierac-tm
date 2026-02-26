# Tasks: 项目立项与治理

> **Spec**: cursor-admin-projects  
> **状态**: 实施中  
> **最后更新**: 2026-02-26

---

## Phase -1：遗留清理（战略转型前置）

> 项目定位已从「粗颗粒度用量监控」转为「贡献可视化 + 项目治理」，以下遗留物需清理。

- [x] **Task C1**：删除 `_tmp/` 目录（cursor-otel-hook、Cursor-LangSmith-Integration 研究用克隆，结论已归档到文档）
- [x] **Task C2**：归档过时文档到 `docs/_archive/`
  - `cursor-admin-hook-granularity.md`（旧 Hook 颗粒度分析，已被新架构替代）
  - `cursor-admin-open-source-hooks-analysis.md`（开源对比，结论已纳入 sierac_core.mdc）
  - `cursor-team-admin-agent-visibility.md`（旧「粗颗粒度用量管理」需求文档，已被新战略替代）
- [x] **Task C3**：删除用户级 Hook 遗留文件（已被项目级 `.cursor/hook/` 替代）
  - `~/.cursor/hooks/cursor_hook.py`
  - `~/.cursor/hooks/hook_config.json`
  - `~/.cursor/hooks.json`
- [x] **Task C4**：更新 `cursor-admin/README.md` 定位（从「粗颗粒度团队用量管理系统」改为新定位）
- [x] **Task C5**：清理 `.pytest_cache/` 目录（项目根目录下的测试缓存）

---

## Phase 0-A：数据模型与项目 CRUD

- [x] **Task 1**：创建 `002_projects.sql` 迁移文件（projects 表、git_contributions 表、agent_sessions 扩展 project_id）
- [x] **Task 2**：Collector 新增项目 CRUD API（`/api/projects` GET/POST/PUT/DELETE）
- [x] **Task 3**：Collector 新增白名单查询 API（`GET /api/projects/whitelist`）
- [x] **Task 4**：管理端新增「项目管理」页面（列表、新建/编辑弹窗、归档）
- [x] **Task 5**：管理端 API client 新增 projects 相关类型与方法
- [x] **Task 6**：管理端导航：新增「项目」入口，替代原「工作目录」

## Phase 0-B：Hook 白名单校验

- [x] **Task 7**：Hook 脚本增加白名单缓存与刷新逻辑（whitelist_cache.json，5 分钟 TTL）
- [x] **Task 8**：Hook `beforeSubmitPrompt` 增加白名单校验（匹配 → continue，不匹配 → 拦截 + 提示）
- [x] **Task 9**：Hook `stop` 上报增加 `project_id` 字段（从 beforeSubmitPrompt 匹配结果传递）
- [x] **Task 10**：Collector `POST /api/sessions` 接收 project_id；若无则根据 workspace_rules 补填

## Phase 0-C：Git 采集与按项目聚合

- [ ] **Task 11**：Collector 新增 Git 采集定时任务（clone/fetch → git log → git diff → upsert git_contributions）
- [ ] **Task 12**：Collector 新增 `/api/projects/{id}/contributions` 查询 API
- [ ] **Task 13**：Collector 新增 `/api/projects/{id}/summary` 汇总 API（成本 + 贡献 + 参与人）
- [ ] **Task 14**：管理端新增「项目详情」页面（成本面板、贡献面板、参与面板）

## Phase 0-D：成员端与收尾

- [ ] **Task 15**：Collector 新增 `/api/contributions/my` API（按当前用户查询所有项目贡献）
- [ ] **Task 16**：管理端新增「我的项目」视图（成员参与的项目列表 + 各项目贡献摘要）
- [ ] **Task 17**：原「工作目录」页改造为按项目聚合视图（未归属会话显示为「未归属」）
- [ ] **Task 18**：端到端验证：立项 → Hook 拦截 → 放行 → 上报归属 → Git 采集 → 管理端展示

## Phase 0-E：GitLab 仓库自动化

- [x] **Task 19**：新增 `.env` 配置项（GITLAB_URL / GITLAB_TOKEN / GITLAB_GROUP_ID / GITLAB_DEFAULT_BRANCH / GITLAB_VISIBILITY）及 `config.py` 对应字段
- [x] **Task 20**：新增 `collector/gitlab_client.py`（GitLab API 封装：创建仓库、推送初始化提交、管理成员、注入 Hook）
- [x] **Task 21**：新增 `collector/hook_templates/` 目录（hooks.json、cursor_hook.py、hook_config.json.tmpl、gitignore.tmpl）
- [x] **Task 22**：扩展 `002_projects.sql`（projects 表增加 gitlab_project_id、repo_url、repo_ssh_url、hook_initialized 字段）（已在 002 中一并创建）
- [x] **Task 23**：修改 `POST /api/projects`（auto_create_repo 参数 → 调用 gitlab_client → 回填字段）
- [x] **Task 24**：新增 `POST /api/projects/{id}/reinject-hook` API（向已有仓库重新注入 Hook 文件）
- [ ] **Task 25**：管理端「新建项目」弹窗增加仓库创建方式选择（自动创建 / 关联已有）、仓库 slug 输入、结果展示（clone 地址一键复制）
- [ ] **Task 26**：管理端项目列表增加仓库状态列（已创建 / 未创建 / 创建失败）和「重试」按钮
- [ ] **Task 27**：端到端验证：立项 → GitLab 仓库创建 → Hook 注入 → 成员 clone → Hook 生效 → 上报归属

---

## 验收清单

- [ ] 管理员可新建/编辑/归档项目
- [ ] Hook 在非白名单目录拦截并给出友好提示
- [ ] Hook 在白名单目录放行且上报归属到正确项目
- [ ] agent_sessions 正确关联 project_id
- [ ] Git 贡献数据按项目按人按日入库
- [ ] 管理端可按项目查看成本与贡献
- [ ] 成员端可看到自己参与的项目与贡献
- [ ] 现有数据（project_id=NULL）正常展示为「未归属」
- [ ] 立项时自动在 GitLab 创建仓库并注入 Hook
- [ ] 成员 clone 仓库后 Hook 自动生效
- [ ] 管理端展示仓库 clone 地址，支持一键复制

---

## 依赖与阻塞

- **内部依赖**：cursor-admin-core（DB 连接、Collector 框架、管理端路由）
- **内部依赖**：cursor-admin-hooks（Hook 脚本扩展）
- **外部依赖**：服务器需安装 git CLI
- **外部依赖**：GitLab API Token（api scope，Phase 0-E）
- **无阻塞项**：可立即启动

---

**维护者**: 团队  
**最后更新**: 2026-02-26
