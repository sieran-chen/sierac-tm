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
nano .env   # 填写 CURSOR_API_TOKEN、POSTGRES_PASSWORD、INTERNAL_API_KEY；DATABASE_URL 中密码与 POSTGRES_PASSWORD 一致。国内服务器若构建时无法访问 deb.debian.org，可增加 APT_MIRROR=http://mirrors.aliyun.com
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

**部署前**：请先将本地修改 **push 到远程**，否则服务器 `git pull` 拉不到最新代码。

可选环境变量：`DEPLOY_HOST`、`DEPLOY_USER`、`REMOTE_REPO`（默认 `REMOTE_REPO=/opt/Sierac-tm`）。

**构建耗时**：首次或 Dockerfile/依赖变更后构建 collector 会较慢（约数分钟）。国内服务器务必在 `.env` 中配置 `APT_MIRROR=http://mirrors.aliyun.com`，否则 apt 可能因访问 deb.debian.org 超时导致构建失败；配置后 apt 步骤会走国内源，通常 1～2 分钟内完成。后续仅改应用代码时，BuildKit 会复用 apt/poetry 等层，只重做最后一两层。

**新版本说明**：Collector 启动时会自动执行 `db/migrations/` 下所有 `.sql`（含 004_github_projects，用于支持 GitHub 立项）。若需立项时自动创建 **GitHub** 仓库，在服务器 `cursor-admin/.env` 中配置 `GITHUB_TOKEN`、可选 `GITHUB_ORG`；GitLab 仍为 `GITLAB_URL`、`GITLAB_TOKEN`、`GITLAB_GROUP_ID`。

---

## 三、阿里云服务器推荐配置

服务器在阿里云 ECS 时，建议做以下配置以加快构建与拉镜象：

1. **Docker 镜像加速**（拉取 python/node/nginx 等基础镜像更快）  
   在服务器上配置 `/etc/docker/daemon.json`，使用阿里云镜像加速器。详见 `cursor-admin/docker/README.md`；示例见 `cursor-admin/docker/daemon-aliyun.json.example`。配置后执行 `sudo systemctl daemon-reload && sudo systemctl restart docker`。

2. **构建与 .env**  
   - 在 `cursor-admin/.env` 中已由 deploy 脚本自动追加或可手动设置：
     - `APT_MIRROR=http://mirrors.aliyun.com`（apt 使用阿里云源）
     - `PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/`（可选，poetry 使用阿里云 PyPI 源）
   - 首次部署或 Dockerfile 变更后构建会稍慢，之后仅改应用代码时 BuildKit 会复用层。

按上述配置后，日常执行 `./deploy.sh` 即可。

---

## 四、清理服务器构建/缓存

若需在服务器上删除 `.venv`、`node_modules`、`__pycache__`、`hook/java/target` 等（例如从旧 scp 部署迁移后）：

```bash
./cleanup-remote.sh
```

默认清理目录为 `REMOTE_REPO/cursor-admin`（即 `/opt/Sierac-tm/cursor-admin`）。若仍用旧路径可指定：`APP_DIR=/opt/cursor-admin ./cleanup-remote.sh`。

---

## 五、验证与防火墙

- 管理端：http://8.130.50.168:3000  
- 采集健康：http://8.130.50.168:8000/health  

云控制台或服务器防火墙需放行 **3000**、**8000**。

---

## 六、Windows 用户

使用 **Git Bash** 或 **WSL** 运行上述脚本即可。

---

## 七、部署方式对比与可选升级

当前方式（**SSH + 服务器上 git pull + docker compose**）在业界很常见，适合单机、小团队：可复现、不传本地编译产物、脚本简单。不算「最先进」，但足够可靠。

若想**更省事**或**更稳妥**，可考虑：

| 方式 | 优点 | 适用 |
|------|------|------|
| **Push 触发自动部署** | 推送后 CI（如 GitHub Actions）SSH 到服务器执行 `git pull && docker compose up`，无需本机跑 `deploy.sh`，有流水线记录。 | 想少一步、多审计 |
| **CI 构建镜像 + 服务器拉镜像** | CI 里构建 Docker 镜像并推到镜像仓库，服务器只 `docker pull` 再启动；回滚=拉旧 tag，环境与构建完全一致。 | 要回滚、多环境一致 |
| **PaaS（Railway / Fly.io / 阿里云 App 等）** | 连 Git 即自动构建部署，不用自管服务器与 SSH；多为按量计费。 | 小项目、优先省心 |

**更简便的一步**：在仓库加一个 GitHub Actions（或 GitLab CI），在 `main` 分支 push 时用 SSH 密钥连接你现有服务器，执行与当前 `deploy.sh` 相同的命令（`cd /opt/Sierac-tm && git pull && cd cursor-admin && docker compose up -d --build`）。这样以后只需 **git push**，无需再在本机执行脚本。
