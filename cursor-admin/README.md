# Cursor Admin — 粗颗粒度团队用量管理系统

## 功能概览

| 模块 | 说明 |
|------|------|
| **用量总览** | 按成员/日期查看 Agent 请求、Chat 请求、Tab 采纳、新增代码行等，含趋势图 |
| **工作目录** | 按成员 + 工作目录汇总会话数与累计时长；支持会话明细分页查询 |
| **支出管理** | 当前计费周期各成员支出、按量请求数、月度上限 |
| **告警规则** | 自定义阈值（每日 Agent 请求数 / 支出），支持邮件 + Webhook 通知 |
| **告警历史** | 查看历史触发记录 |

## 系统架构

```
成员机器（Cursor IDE）
  └── ~/.cursor/hooks.json          ← 仅监听 stop + beforeSubmitPrompt
  └── ~/.cursor/hooks/cursor_hook.jar   (Java，JRE 11+)
        │  每次 Agent 会话结束 → 1 条 HTTP POST
        ▼
服务器（Docker Compose）
  ┌─────────────────────────────────────┐
  │  collector（FastAPI :8000）          │
  │  ├── POST /api/sessions  ← Hook 上报 │
  │  ├── 定时拉取 Cursor Admin API        │
  │  │   （每小时：成员/用量/支出）        │
  │  └── GET /api/...  ← 管理端查询       │
  │                                     │
  │  db（PostgreSQL :5432）              │
  │  ├── members                        │
  │  ├── daily_usage                    │
  │  ├── spend_snapshots                │
  │  ├── agent_sessions  ← Hook 数据     │
  │  ├── alert_rules                    │
  │  └── alert_events                   │
  │                                     │
  │  web（Nginx :3000）                  │
  │  └── React 管理端                    │
  └─────────────────────────────────────┘
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

## 二、客户端 Hook 分发（成员机器）

Hook 为 **Java** 实现（团队统一技术栈），需 **JRE 11+**。部署到每台成员机器的 `~/.cursor/hooks/` 目录，并配置 `~/.cursor/hooks.json`。

### 成员不装 Hook 会怎样？

| 能力 | 数据来源 | 不装 Hook 时 |
|------|----------|--------------|
| 用量总览、支出管理、告警（基于用量/支出） | 服务端定时拉取 **Cursor Admin API** | ✅ 正常，全员可见 |
| 工作目录（按目录的会话数、时长、会话明细） | 仅来自 **Hook 上报** | ❌ 该成员无此数据 |

因此：不装 Hook 只会缺失「工作目录/会话」细粒度数据；用量与支出仍可从 Cursor 官方 API 获得。若希望工作目录数据覆盖全员，建议用 **方式 B（MDM 批量推送）** 统一部署，或通过规范要求成员安装。

### 构建 JAR（一次性，在任意有 Maven 的机器上）

```bash
cd cursor-admin/hook/java
mvn -q package
# 产物：hook/java/target/cursor_hook.jar（含依赖的 fat JAR）
```

可将 `cursor_hook.jar` 放到内网文件共享或 MDM 分发目录，供安装脚本使用。

### 方式 A：手动安装（少量成员）

**macOS / Linux**

```bash
# 确保同目录下已有 cursor_hook.jar（或已执行上面 mvn package，则存在 java/target/cursor_hook.jar）
COLLECTOR_URL=http://your-server:8000 \
USER_EMAIL=member@company.com \
bash install.sh
```

**Windows（PowerShell）**

```powershell
$env:COLLECTOR_URL = "http://your-server:8000"
$env:USER_EMAIL    = "member@company.com"
.\install.ps1
```

### 方式 B：MDM 批量推送（推荐，多成员）

**macOS（Jamf Pro）**

1. 将 `hook/cursor_hook.py` 和 `hook/install.sh` 打包或上传到 Jamf。
2. 创建 Policy，添加 Script，内容如下：

```bash
#!/bin/bash
export COLLECTOR_URL="http://your-server:8000"
export USER_EMAIL="$(/usr/bin/python3 -c "import subprocess; print(subprocess.check_output(['id','-un']).decode().strip())")@company.com"
# 或从 LDAP/AD 查询真实邮箱
bash /path/to/install.sh
```

**Windows（Intune / GPO）**

1. 将 `cursor_hook.py` 和 `install.ps1` 放到共享路径（如 `\\fileserver\cursor-hook\`）。
2. 创建 PowerShell 脚本策略：

```powershell
$env:COLLECTOR_URL = "http://your-server:8000"
$env:USER_EMAIL    = "$env:USERNAME@company.com"
& "\\fileserver\cursor-hook\install.ps1"
```

### Hook 配置说明

安装后，每台机器的 `~/.cursor/hooks.json` 会指向 Java JAR：

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      { "command": "java -jar ~/.cursor/hooks/cursor_hook.jar" }
    ],
    "stop": [
      { "command": "java -jar ~/.cursor/hooks/cursor_hook.jar" }
    ]
  }
}
```

- `beforeSubmitPrompt`：仅在本地记录会话开始时间（不上报，不消耗 token）。
- `stop`：会话结束时上报 1 条记录（workspace_roots + 时长），HTTP POST 到采集服务。
- 要求本机已安装 **JRE 11+**（`java -version` 可验证）。
- 若个别机器无 Java，可改用同目录下的 `cursor_hook.py`（Python 3），将 `hooks.json` 中的命令改为 `python3 ~/.cursor/hooks/cursor_hook.py`，行为与 JAR 一致。

### 验证 Hook 是否生效

```bash
# macOS/Linux
echo '{"hook_event_name":"stop","conversation_id":"test-123","workspace_roots":["/tmp/test"]}' \
  | java -jar ~/.cursor/hooks/cursor_hook.jar
```

应输出 `{"continue":true}` 且采集服务日志中出现对应记录。

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
│   ├── alerts.py         # 告警检测与通知
│   ├── cursor_api.py     # Cursor API 客户端
│   ├── database.py       # 数据库连接与迁移
│   ├── config.py         # 配置（读取环境变量）
│   ├── pyproject.toml    # Poetry 依赖与 Ruff/pytest 配置
│   ├── poetry.lock       # 锁定依赖版本（提交到仓库）
│   └── Dockerfile
├── db/
│   └── migrations/
│       └── 001_init.sql  # 数据库 Schema（幂等）
├── hook/                 # 客户端 Hook（Java，部署到成员机器）
│   ├── java/             # Maven 工程，构建 cursor_hook.jar
│   │   ├── pom.xml
│   │   └── src/main/java/com/cursor/hook/CursorHook.java
│   ├── hook_config.json  # 配置模板
│   ├── hooks.json        # Cursor hooks.json 模板
│   ├── install.sh        # macOS/Linux 安装脚本
│   └── install.ps1       # Windows 安装脚本
└── web/                  # 管理端（React / Vite / Tailwind）
    ├── src/
    │   ├── api/client.ts # API 客户端 + 类型定义
    │   ├── components/   # Layout
    │   ├── pages/        # 用量/工作目录/支出/告警/历史
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
