# 部署到公网服务器（Git 方式）

**部署方式**：服务器上通过 `git pull` 拉取代码后执行 `docker compose`，不再从本机 scp/rsync 上传。

**安全提醒**：请勿将服务器密码或 API 密钥提交到仓库。建议配置 SSH 密钥登录（运行 `./setup-ssh-keys.sh`）。  
**不应提交**：根目录 `.gitignore` 已配置，以下不会上传：`.env`、`.venv`/`node_modules`、`__pycache__`/`.pytest_cache`/`.ruff_cache`、`web/dist`、`hook/java/target`、IDE/系统临时文件等；仅保留 `.env.example` 作为模板。

---

## 一、首次部署（服务器尚未 clone 仓库）

### 1. 本机：清理服务器上的旧构建/缓存（若之前用过 scp 部署）

若服务器上仍是旧目录 `/opt/cursor-admin`（无 Git），先清理垃圾再迁移：

```bash
cd cursor-admin
APP_DIR=/opt/cursor-admin bash cleanup-remote.sh
```

### 2. 服务器：clone 仓库并配置 .env

SSH 登录后执行（将 `你的仓库地址` 换成实际 Git 地址，如 `git@github.com:your/Sierac-tm.git` 或 HTTPS）：

```bash
ssh root@8.130.50.168

# 若之前是 /opt/cursor-admin，可保留 .env 后改用新目录
sudo mkdir -p /opt/Sierac-tm
sudo git clone 你的仓库地址 /opt/Sierac-tm
cd /opt/Sierac-tm/cursor-admin
cp .env.example .env
nano .env   # 填写 CURSOR_API_TOKEN、POSTGRES_PASSWORD、INTERNAL_API_KEY；DATABASE_URL 中密码与 POSTGRES_PASSWORD 一致
```

若已有 `/opt/cursor-admin/.env`，可直接复制：

```bash
cp /opt/cursor-admin/.env /opt/Sierac-tm/cursor-admin/.env
```

### 3. 本机：执行部署

```bash
cd cursor-admin
./deploy.sh
```

---

## 二、日常部署（仓库已 clone 在服务器）

本地改完代码并 **push 到远程** 后，在 **cursor-admin** 目录执行：

```bash
./deploy.sh
```

脚本会在服务器上执行：`cd /opt/Sierac-tm && git pull && cd cursor-admin && docker compose up -d --build`。

可选环境变量：`DEPLOY_HOST`、`DEPLOY_USER`、`REMOTE_REPO`（默认 `REMOTE_REPO=/opt/Sierac-tm`）。

---

## 三、清理服务器构建/缓存

若需在服务器上删除 `.venv`、`node_modules`、`__pycache__`、`hook/java/target` 等（例如从旧 scp 部署迁移后）：

```bash
./cleanup-remote.sh
```

默认清理目录为 `REMOTE_REPO/cursor-admin`（即 `/opt/Sierac-tm/cursor-admin`）。若仍用旧路径可指定：`APP_DIR=/opt/cursor-admin ./cleanup-remote.sh`。

---

## 四、验证与防火墙

- 管理端：http://8.130.50.168:3000  
- 采集健康：http://8.130.50.168:8000/health  

云控制台或服务器防火墙需放行 **3000**、**8000**。

---

## 五、Windows 用户

使用 **Git Bash** 或 **WSL** 运行上述脚本即可。

---

## 六、部署方式对比与可选升级

当前方式（**SSH + 服务器上 git pull + docker compose**）在业界很常见，适合单机、小团队：可复现、不传本地编译产物、脚本简单。不算「最先进」，但足够可靠。

若想**更省事**或**更稳妥**，可考虑：

| 方式 | 优点 | 适用 |
|------|------|------|
| **Push 触发自动部署** | 推送后 CI（如 GitHub Actions）SSH 到服务器执行 `git pull && docker compose up`，无需本机跑 `deploy.sh`，有流水线记录。 | 想少一步、多审计 |
| **CI 构建镜像 + 服务器拉镜像** | CI 里构建 Docker 镜像并推到镜像仓库，服务器只 `docker pull` 再启动；回滚=拉旧 tag，环境与构建完全一致。 | 要回滚、多环境一致 |
| **PaaS（Railway / Fly.io / 阿里云 App 等）** | 连 Git 即自动构建部署，不用自管服务器与 SSH；多为按量计费。 | 小项目、优先省心 |

**更简便的一步**：在仓库加一个 GitHub Actions（或 GitLab CI），在 `main` 分支 push 时用 SSH 密钥连接你现有服务器，执行与当前 `deploy.sh` 相同的命令（`cd /opt/Sierac-tm && git pull && cd cursor-admin && docker compose up -d --build`）。这样以后只需 **git push**，无需再在本机执行脚本。
