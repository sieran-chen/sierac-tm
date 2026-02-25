# 与 Cursor 官方 Admin API 打通

管理端要显示**成员、用量、支出**等数据，必须配置 **Cursor Admin API 密钥**，采集服务会定时向官方 API 拉取并写入数据库。

---

## 一、获取 Cursor Admin API Key（官方）

1. 使用 **Team 或 Enterprise** 的**管理员账号**登录 [Cursor](https://cursor.com)。
2. 打开 **cursor.com/dashboard** → **Settings** → **Advanced** → **Admin API Keys**。
3. 点击 **Create New API Key**，命名（如 `sierac-tm-dashboard`），复制生成的 Key。  
   - 格式类似：`key_xxxxxxxxxxxxxxxx...`  
   - **只显示一次**，请妥善保存。

参考：[Cursor Docs - Admin API](https://docs.cursor.com/account/teams/admin-api)

---

## 二、本仓库与官方 API 的对应关系

| 本仓库（cursor_api.py） | Cursor 官方端点 | 用途 |
|-------------------------|------------------|------|
| `get_members()` | `GET /teams/members` | 同步成员列表 → `members` 表 |
| `get_daily_usage()` | `POST /teams/daily-usage-data` | 同步每日用量 → `daily_usage` 表 |
| `get_spend()` | `POST /teams/spend` | 同步支出 → `spend_snapshots` 表 |

认证方式：**Basic Auth**，用户名为 API Key，密码为空（本仓库已按此实现）。

---

## 三、配置到服务器并拉取数据

### 方式 A：用脚本写入并重启（推荐）

在**本机**项目根或 `cursor-admin` 目录执行（将 `key_xxx...` 换成你的真实 Key）：

```bash
cd cursor-admin
CURSOR_API_TOKEN=key_你的完整Key ./configure-cursor-api.sh
```

脚本会通过 SSH 在服务器上更新 `cursor-admin/.env` 中的 `CURSOR_API_TOKEN`，并重启 collector，下次定时同步（或启动时同步）会拉取数据。

### 方式 B：手动 SSH 配置

```bash
ssh root@8.130.50.168   # 或你的服务器
cd /opt/Sierac-tm/cursor-admin
nano .env   # 将 CURSOR_API_TOKEN= 改为你的 Key，保存
docker compose restart collector
```

---

## 四、验证是否打通

- 管理端刷新 **用量总览 / 支出管理** 等页，应能看到成员与数据（取决于你 Team 的实际用量）。
- 或在服务器上执行自检（会调用带 key 的 API）：  
  `cd /opt/Sierac-tm/cursor-admin && bash verify-service.sh`  
  若 `/api/members` 返回非空数组，说明 API 已打通。

若仍无数据，请检查：

- `CURSOR_API_TOKEN` 是否完整、无多余空格。
- 该 Key 是否为 **Admin API Key**（Team/Enterprise 管理员在 dashboard 创建）。
- 服务器时间是否正常（同步用时间范围）。
