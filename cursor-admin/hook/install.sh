#!/bin/bash
# Hook 安装脚本（macOS / Linux）
# 前置：已构建 JAR，见下方。用法：COLLECTOR_URL=http://your-server:8000 USER_EMAIL=you@company.com bash install.sh

set -e

HOOKS_DIR="$HOME/.cursor/hooks"
mkdir -p "$HOOKS_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 优先使用同目录下已构建的 cursor_hook.jar，否则用 java/target/cursor_hook.jar
JAR_SRC="$SCRIPT_DIR/cursor_hook.jar"
[ -f "$JAR_SRC" ] || JAR_SRC="$SCRIPT_DIR/java/target/cursor_hook.jar"
if [ ! -f "$JAR_SRC" ]; then
  echo "未找到 cursor_hook.jar。请先构建："
  echo "  cd $SCRIPT_DIR/java && mvn -q package"
  echo "然后重新运行本安装脚本。"
  exit 1
fi

cp "$JAR_SRC" "$HOOKS_DIR/cursor_hook.jar"

# 写入配置（优先使用环境变量）
COLLECTOR_URL="${COLLECTOR_URL:-http://localhost:8000}"
USER_EMAIL="${USER_EMAIL:-}"

cat > "$HOOKS_DIR/hook_config.json" <<EOF
{
  "collector_url": "$COLLECTOR_URL",
  "user_email": "$USER_EMAIL",
  "machine_id": "",
  "timeout_seconds": 5,
  "state_dir": "$HOOKS_DIR/.state"
}
EOF

# 写入 hooks.json（用户级，全局生效）- 使用 Java 运行 JAR
cat > "$HOME/.cursor/hooks.json" <<'HOOKSEOF'
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      {
        "command": "java -jar ~/.cursor/hooks/cursor_hook.jar"
      }
    ],
    "stop": [
      {
        "command": "java -jar ~/.cursor/hooks/cursor_hook.jar"
      }
    ]
  }
}
HOOKSEOF

echo "✓ Cursor hook (Java) installed."
echo "  Collector: $COLLECTOR_URL"
echo "  User:      ${USER_EMAIL:-auto-detect}"
echo "  Config:    $HOOKS_DIR/hook_config.json"
echo "  要求:      JRE 11+ (java -version)"
