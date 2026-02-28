#!/usr/bin/env bash
# 基于 Git 的部署：在服务器上 git pull 后执行 docker compose（不再上传本地文件）
# 前置：服务器已 clone 仓库到 REMOTE_REPO，且 cursor-admin/.env 已配置
set -e
DEPLOY_HOST="${DEPLOY_HOST:-8.130.50.168}"
DEPLOY_USER="${DEPLOY_USER:-root}"
REMOTE_REPO="${REMOTE_REPO:-/opt/Sierac-tm}"
APP_DIR="${REMOTE_REPO}/cursor-admin"

echo ">>> 在 ${DEPLOY_USER}@${DEPLOY_HOST} 上拉取代码并构建..."
# 阿里云服务器：未配置时自动追加 APT/PIP 镜像，加速构建；BuildKit 改善层缓存
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "cd ${REMOTE_REPO} && git pull && cd cursor-admin && (test -f .env || (cp .env.example .env && echo '请 SSH 登录编辑 cursor-admin/.env 后重新执行 deploy.sh' && exit 1)) && (grep -q '^APT_MIRROR=' .env 2>/dev/null || echo 'APT_MIRROR=http://mirrors.aliyun.com' >> .env) && (grep -q '^PIP_INDEX_URL=' .env 2>/dev/null || echo 'PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/' >> .env) && DOCKER_BUILDKIT=1 docker compose up -d --build"

echo ">>> 部署完成。管理端: http://${DEPLOY_HOST}:3000  采集健康: http://${DEPLOY_HOST}:8000/health"