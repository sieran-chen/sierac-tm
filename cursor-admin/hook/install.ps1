# Hook 安装脚本（Windows PowerShell）
# 前置：已构建 JAR。用法：$env:COLLECTOR_URL="http://your-server:8000"; $env:USER_EMAIL="you@company.com"; .\install.ps1

param(
    [string]$CollectorUrl = $env:COLLECTOR_URL,
    [string]$UserEmail    = $env:USER_EMAIL
)

if (-not $CollectorUrl) { $CollectorUrl = "http://localhost:8000" }

$HooksDir = "$env:USERPROFILE\.cursor\hooks"
New-Item -ItemType Directory -Force -Path $HooksDir | Out-Null
New-Item -ItemType Directory -Force -Path "$HooksDir\.state" | Out-Null

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$JarSrc = Join-Path $ScriptDir "cursor_hook.jar"
if (-not (Test-Path $JarSrc)) {
  $JarSrc = Join-Path $ScriptDir "java\target\cursor_hook.jar"
}
if (-not (Test-Path $JarSrc)) {
  Write-Host "未找到 cursor_hook.jar。请先构建："
  Write-Host "  cd $ScriptDir\java"
  Write-Host "  mvn -q package"
  Write-Host "然后重新运行本安装脚本。"
  exit 1
}
Copy-Item $JarSrc "$HooksDir\cursor_hook.jar" -Force

# 写入配置
$config = @{
    collector_url    = $CollectorUrl
    user_email       = $UserEmail
    machine_id       = ""
    timeout_seconds  = 5
    state_dir        = "$HooksDir\.state"
} | ConvertTo-Json -Depth 3
Set-Content -Path "$HooksDir\hook_config.json" -Value $config -Encoding UTF8

# 写入 hooks.json（用户级）- 使用 Java 运行 JAR
$hooksJson = @"
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      { "command": "java -jar $HooksDir\cursor_hook.jar" }
    ],
    "stop": [
      { "command": "java -jar $HooksDir\cursor_hook.jar" }
    ]
  }
}
"@
Set-Content -Path "$env:USERPROFILE\.cursor\hooks.json" -Value $hooksJson -Encoding UTF8

Write-Host "Hook (Java) installed."
Write-Host "  Collector : $CollectorUrl"
Write-Host "  User      : $(if ($UserEmail) { $UserEmail } else { 'auto-detect' })"
Write-Host "  Config    : $HooksDir\hook_config.json"
Write-Host "  要求      : JRE 11+ (java -version)"
