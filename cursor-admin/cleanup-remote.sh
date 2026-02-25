#!/usr/bin/env bash
# 清理服务器上由旧版 scp/rsync 部署产生的构建与缓存目录（仅删这些目录，不动 .env 和代码）
# 若已改为 Git 部署，APP_DIR 应为仓库下的 cursor-admin，如 /opt/Sierac-tm/cursor-admin
set -e
DEPLOY_HOST="${DEPLOY_HOST:-8.130.50.168}"
DEPLOY_USER="${DEPLOY_USER:-root}"
REMOTE_REPO="${REMOTE_REPO:-/opt/Sierac-tm}"
APP_DIR="${APP_DIR:-${REMOTE_REPO}/cursor-admin}"

echo ">>> 清理 ${DEPLOY_USER}@${DEPLOY_HOST}:${APP_DIR} 下的构建/缓存目录..."
ssh "${DEPLOY_USER}@${DEPLOY_HOST}" "cd ${APP_DIR} && \
  rm -rf collector/.venv collector/.pytest_cache collector/.ruff_cache \
         web/node_modules web/dist hook/java/target 2>/dev/null; \
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
  echo '清理完成。'"
