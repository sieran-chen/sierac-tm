#!/usr/bin/env bash
# 在服务器上运行：检查 cursor-admin 服务是否完好（健康、API 鉴权、数据库）
# 用法：在服务器上 cd /opt/Sierac-tm/cursor-admin && bash verify-service.sh
# 或从本机：ssh root@8.130.50.168 "cd /opt/Sierac-tm/cursor-admin && bash verify-service.sh"
set -e
cd "$(dirname "$0")"
BASE="${BASE:-http://localhost:8000}"

echo ">>> 1. 容器状态"
docker compose ps 2>/dev/null || true

echo ""
echo ">>> 2. 健康检查 GET ${BASE}/health"
curl -sS "${BASE}/health" && echo "" || { echo "失败"; exit 1; }

echo ""
echo ">>> 3. 带 x-api-key 的 API（需 .env 中 INTERNAL_API_KEY）"
if [ -f .env ]; then
  KEY=$(grep "^INTERNAL_API_KEY=" .env | cut -d= -f2- | tr -d '\r')
  if [ -n "$KEY" ]; then
    CODE=$(curl -sS -o /tmp/verify_members.json -w "%{http_code}" -H "x-api-key: ${KEY}" "${BASE}/api/members")
    echo "GET /api/members -> HTTP $CODE"
    [ "$CODE" = "200" ] && echo "  内容预览: $(head -c 120 /tmp/verify_members.json)..."
    CODE2=$(curl -sS -o /tmp/verify_rules.json -w "%{http_code}" -H "x-api-key: ${KEY}" "${BASE}/api/alerts/rules")
    echo "GET /api/alerts/rules -> HTTP $CODE2"
  else
    echo "  跳过（INTERNAL_API_KEY 为空）"
  fi
else
  echo "  跳过（无 .env）"
fi

echo ""
echo ">>> 4. Web -> Collector 内网连通"
docker exec cursor-admin-web-1 wget -q -O- http://collector:8000/health 2>/dev/null && echo "  OK" || echo "  失败"

echo ""
echo ">>> 服务自检结束"
