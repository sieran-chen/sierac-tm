#!/usr/bin/env bash
# 首次部署：在服务器上 clone 仓库并准备 .env（只需执行一次，之后用 deploy.sh）
# 前置：代码已 push 到 https://github.com/sieran-chen/sierac-tm
set -e
DEPLOY_HOST="${DEPLOY_HOST:-8.130.50.168}"
DEPLOY_USER="${DEPLOY_USER:-root}"
REMOTE_REPO="${REMOTE_REPO:-/opt/Sierac-tm}"
REPO_URL="${REPO_URL:-https://github.com/sieran-chen/sierac-tm.git}"

echo ">>> 在 ${DEPLOY_USER}@${DEPLOY_HOST} 上 clone 仓库到 ${REMOTE_REPO} ..."
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "bash -s" << REMOTE
set -e
if [ -d "${REMOTE_REPO}/.git" ]; then
  echo "仓库已存在，跳过 clone。"
  exit 0
fi
mkdir -p $(dirname ${REMOTE_REPO})
git clone ${REPO_URL} ${REMOTE_REPO}
cd ${REMOTE_REPO}/cursor-admin
if [ -f /opt/cursor-admin/.env ]; then
  cp /opt/cursor-admin/.env .env && echo "已从 /opt/cursor-admin 复制 .env"
else
  cp .env.example .env && echo "已创建 .env，请 SSH 登录编辑: nano ${REMOTE_REPO}/cursor-admin/.env"
fi
REMOTE
echo ">>> 完成。请确认 cursor-admin/.env 已填写正确后执行: ./deploy.sh"