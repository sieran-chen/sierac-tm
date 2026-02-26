# Sierac-tm — AI 团队贡献可视化与激励平台

> 前身为 Cursor Admin（粗颗粒度用量管理），现已升级为以**项目立项**为核心、以**贡献可视化**驱动团队积极性的管理平台。

## 功能概览

| 模块 | 说明 |
|------|------|
| **项目管理** | 项目立项（白名单）、成本归属、贡献聚合、项目生命周期管理 |
| **用量总览** | 按成员/日期查看 Agent 请求、Chat 请求、Tab 采纳、新增代码行等，含趋势图 |
| **贡献面板** | 按项目/按人聚合 Git 提交、代码量、Cursor 使用等多维度贡献数据 |
| **支出管理** | 当前计费周期各成员支出、按量请求数、月度上限，按项目归属 |
| **告警规则** | 自定义阈值（每日 Agent 请求数 / 支出），支持邮件 + Webhook 通知 |
| **告警历史** | 查看历史触发记录 |
| **我的项目**（成员端） | 成员查看自己参与的项目、贡献摘要、排名 |

## 系统架构

```
成员机器（Cursor IDE）
  └── .cursor/hooks.json              ← 项目级 Hook（推荐）
  └── .cursor/hook/cursor_hook.py     ← Python Hook 脚本
        │  白名单校验 + 会话归属上报
        ▼
服务器（Docker Compose）
  ┌──────────────────────────────────────────┐
  │  collector（FastAPI :8000）               │
  │  ├── POST /api/sessions    ← Hook 上报   │
  │  ├── /api/projects         ← 项目 CRUD   │
  │  ├── /api/projects/whitelist ← 白名单    │
  │  ├── git_sync.py           ← Git 贡献采集 │
  │  ├── 定时拉取 Cursor Admin API            │
  │  └── GET /api/...          ← 管理端查询   │
  │                                          │
  │  db（PostgreSQL :5432）                   │
  │  ├── projects              ← 项目立项     │
  │  ├── members                             │
  │  ├── daily_usage                         │
  │  ├── spend_snapshots                     │
  │  ├── agent_sessions (+project_id)        │
  │  ├── git_contributions     ← Git 贡献     │
  │  ├── alert_rules                         │
  │  └── alert_events                        │
  │                                          │
  │  web（Nginx :3000）                       │
  │  └── React 管理端 + 成员端                │
  └──────────────────────────────────────────┘
```

---

## 一、服务端部署（Docker Compose）

### 前置要求

- Docker 20.10+
- Docker Compose v2
- 服务器开放端口：3000（管理端）、8000（采集服务，仅内网或 VPN 可访问）

### 步骤

**1. 克隆/复制本目录到服务器**

```bash
scp -r cursor-admin/ user@your-server:/opt/cursor-admin
ssh user@your-server
cd /opt/cursor-admin
```

**2. 配置环境变量**

```bash
cp .env.example .env
nano .env   # 或 vim .env
```

必填项：

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `CURSOR_API_TOKEN` | Cursor Admin API 密钥（**无则管理端无数据**） | [cursor.com/dashboard](https://cursor.com/dashboard) → Settings → Advanced → Admin API Keys；详见 [docs/CURSOR-API-SETUP.md](../docs/CURSOR-API-SETUP.md) |
| `POSTGRES_PASSWORD` | 数据库密码 | 自定义，强密码 |
| `INTERNAL_API_KEY` | 管理端与采集服务通信密钥 | 自定义，随机字符串 |

配置好 `CURSOR_API_TOKEN` 后，可用脚本写入服务器并重启采集服务：  
`CURSOR_API_TOKEN=key_xxx ./configure-cursor-api.sh`

可选项（邮件告警）：

```
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your@qq.com
SMTP_PASSWORD=your_smtp_password
SMTP_FROM=your@qq.com
SMTP_USE_SSL=true
```

可选项（企业微信/钉钉 Webhook）：

```
DEFAULT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

**3. 启动服务**

```bash
docker compose up -d --build
```

**4. 验证**

```bash
# 采集服务健康检查
curl http://localhost:8000/health

# 管理端
open http://your-server:3000
```

**5. 查看日志**

```bash
docker compose logs -f collector   # 采集服务日志（含同步状态）
docker compose logs -f db
```

### 数据持久化

PostgreSQL 数据存储在 Docker named volume `pg_data`，重启/更新不会丢失。

备份：

```bash
docker compose exec db pg_dump -U cursor cursor_admin > backup_$(date +%Y%m%d).sql
```

恢复：

```bash
cat backup_20260101.sql | docker compose exec -T db psql -U cursor cursor_admin
```

---

## 二、客户端 Hook 分发

Hook 为 **Python** 实现，推荐以**项目级**方式部署（`.cursor/hook/`），每个项目仓库自带 Hook 脚本和配置。

### 项目级 Hook（推荐）

将以下文件放入项目仓库的 `.cursor/` 目录：

```
your-project/
├── .cursor/
│   ├── hooks.json           # Hook 注册（指向 hook/cursor_hook.py）
│   └── hook/
│       ├── cursor_hook.py   # Hook 脚本（白名单校验 + 会话上报）
│       └── hook_config.json # Collector 地址、用户邮箱等配置
```

成员 clone 项目后，Cursor 自动识别 `.cursor/hooks.json`，无需额外安装。

### Hook 工作流程

1. **`beforeSubmitPrompt`**：校验当前工作目录是否在白名单项目中
   - 匹配 → `{"continue": true}`，放行
   - 不匹配 → 拦截并提示「请先在管理平台立项」
2. **`stop`**：上报会话归属（workspace + project_id + 时长）到 Collector

### 不装 Hook 会怎样？

| 能力 | 数据来源 | 无 Hook 时 |
|------|----------|------------|
| 用量总览、支出管理、告警 | Cursor Admin API（服务端拉取） | 正常 |
| 项目归属、贡献关联 | Hook 上报 | 该成员无归属数据 |
| Git 贡献 | 服务端 Git 采集 | 正常（不依赖 Hook） |

### 全局 Hook（备选，用于未立项场景）

若需在所有项目中启用 Hook（含未纳入版本控制的项目），可使用全局安装脚本：

```bash
# macOS/Linux
COLLECTOR_URL=http://your-server:8000 USER_EMAIL=member@company.com bash install.sh

# Windows
$env:COLLECTOR_URL = "http://your-server:8000"
$env:USER_EMAIL = "member@company.com"
.\install.ps1
```

### 验证 Hook 是否生效

```bash
echo '{"hook_event_name":"stop","conversation_id":"test-123","workspace_roots":["/tmp/test"]}' \
  | python3 .cursor/hook/cursor_hook.py
```

应输出 `{"continue":true}` 且 Collector 日志中出现对应记录。

---

## 三、告警配置

在管理端 **告警规则** 页面新建规则：

| 字段 | 说明 |
|------|------|
| 规则名称 | 如"张三每日 Agent 请求超限" |
| 指标 | 每日 Agent 请求数 / 当前周期支出（分）/ 月度支出（分） |
| 范围 | 指定成员 或 全团队 |
| 阈值 | 超过此值触发告警 |
| 通知渠道 | 邮件（填收件地址）或 Webhook（填企业微信/钉钉 URL） |

告警冷却：同一规则 1 小时内最多触发 1 次，避免重复轰炸。

---

## 四、升级与维护

**更新服务**

```bash
cd /opt/cursor-admin
git pull   # 或重新上传文件
docker compose up -d --build
```

**数据库迁移**

新版本若有新的 `db/migrations/*.sql`，服务启动时会自动执行（幂等）。

**调整同步频率**

修改 `.env` 中的 `SYNC_INTERVAL_MINUTES`（默认 60 分钟），重启 collector 生效。

---

## 五、目录结构

```
cursor-admin/
├── .env.example          # 环境变量模板
├── docker-compose.yml    # 一键部署
├── collector/            # 采集服务（Python / FastAPI）
│   ├── main.py           # 入口：HTTP API + 定时任务
│   ├── sync.py           # 从 Cursor Admin API 同步数据
│   ├── git_sync.py       # Git 仓库贡献采集（定时 clone/fetch → git log）
│   ├── alerts.py         # 告警检测与通知
│   ├── cursor_api.py     # Cursor API 客户端
│   ├── database.py       # 数据库连接与迁移
│   ├── config.py         # 配置（读取环境变量）
│   ├── pyproject.toml    # Poetry 依赖与 Ruff/pytest 配置
│   ├── poetry.lock       # 锁定依赖版本（提交到仓库）
│   └── Dockerfile
├── db/
│   └── migrations/
│       ├── 001_init.sql      # 基础 Schema（幂等）
│       └── 002_projects.sql  # 项目立项 + Git 贡献表
├── hook/                 # Hook 模板与全局安装脚本
│   ├── cursor_hook.py    # Python Hook 脚本（模板）
│   ├── hook_config.json  # 配置模板
│   ├── hooks.json        # Cursor hooks.json 模板
│   ├── install.sh        # macOS/Linux 全局安装脚本
│   └── install.ps1       # Windows 全局安装脚本
└── web/                  # 管理端 + 成员端（React / Vite / Tailwind）
    ├── src/
    │   ├── api/client.ts # API 客户端 + 类型定义
    │   ├── components/   # Layout、共享组件
    │   ├── pages/        # 项目管理/用量/贡献/支出/告警/我的项目
    │   └── App.tsx
    ├── nginx.conf
    └── Dockerfile
```

---

## 六、本地开发（Collector）

采集服务使用 **Poetry** 管理依赖，Python 3.10+。

```bash
cd cursor-admin/collector
poetry install          # 安装生产 + 开发依赖
poetry run pytest       # 运行测试
poetry run ruff check . # 静态检查
poetry run ruff format . # 格式化
poetry run python -m uvicorn main:app --reload  # 本地启动（需配置 .env / DATABASE_URL）
```

首次克隆或新增依赖后请执行 `poetry lock` 并提交 `poetry.lock`，以保证 CI/Docker 构建一致。
