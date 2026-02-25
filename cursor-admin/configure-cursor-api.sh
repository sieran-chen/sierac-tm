#!/usr/bin/env bash
# 将 CURSOR_API_TOKEN 写入服务器 .env 并重启 collector，与 Cursor 官方 API 打通后即可看到数据
# 用法：CURSOR_API_TOKEN=key_xxx ./configure-cursor-api.sh
set -e
DEPLOY_HOST="${DEPLOY_HOST:-8.130.50.168}"
DEPLOY_USER="${DEPLOY_USER:-root}"
REMOTE_REPO="${REMOTE_REPO:-/opt/Sierac-tm}"
APP_DIR="${REMOTE_REPO}/cursor-admin"

if [ -z "${CURSOR_API_TOKEN}" ]; then
  echo "请设置 CURSOR_API_TOKEN，例如："
  echo "  CURSOR_API_TOKEN=key_你的完整Key ./configure-cursor-api.sh"
  echo "Key 在 cursor.com/dashboard → Settings → Advanced → Admin API Keys 创建。"
  exit 1
fi

echo ">>> 在 ${DEPLOY_USER}@${DEPLOY_HOST} 上更新 .env 并重启 collector..."
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "bash -s" "${CURSOR_API_TOKEN}" "${APP_DIR}" << 'REMOTE'
TOKEN="$1"
APP_DIR="$2"
cd "$APP_DIR"
if grep -q '^CURSOR_API_TOKEN=' .env 2>/dev/null; then
  sed -i "s|^CURSOR_API_TOKEN=.*|CURSOR_API_TOKEN=${TOKEN}|" .env
else
  echo "CURSOR_API_TOKEN=${TOKEN}" >> .env
fi
docker compose restart collector
echo "已更新 CURSOR_API_TOKEN 并重启 collector。稍等约 1 分钟后刷新管理端即可看到数据。"
REMOTE
