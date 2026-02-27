#!/usr/bin/env bash
# 在 cursor-admin 目录下执行，仅构建 collector 镜像（用于排查构建问题）
# 用法：./build-collector.sh  或  bash build-collector.sh
set -e
echo ">>> Building collector image (context: $(pwd))..."
docker compose build --progress=plain collector 2>&1
echo ">>> Build done. Start with: docker compose up -d collector"
