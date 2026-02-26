# Hook 安装脚本（Windows PowerShell）
# 用法：$env:COLLECTOR_URL="http://your-server:8000"; $env:USER_EMAIL="you@company.com"; .\install.ps1
# 优先用 JAR；无 JAR 时自动用同目录的 cursor_hook.py（需 Python 3）

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
$PySrc = Join-Path $ScriptDir "cursor_hook.py"

$usePython = $false
if (Test-Path $JarSrc) {
  Copy-Item $JarSrc "$HooksDir\cursor_hook.jar" -Force
} elseif (Test-Path $PySrc) {
  Copy-Item $PySrc "$HooksDir\cursor_hook.py" -Force
  $usePython = $true
} else {
  Write-Host "未找到 cursor_hook.jar 或 cursor_hook.py。请从 repo 的 hook 目录运行本脚本。"
  exit 1
}

# 写入配置
$config = @{
    collector_url    = $CollectorUrl
    user_email       = $UserEmail
    machine_id       = ""
    timeout_seconds  = 5
    state_dir        = "$HooksDir\.state"
} | ConvertTo-Json -Depth 3
Set-Content -Path "$HooksDir\hook_config.json" -Value $config -Encoding UTF8

# 写入 hooks.json（用户级）：命令中的 \ 和 " 需按 JSON 转义
$hookCmd = if ($usePython) {
  "py -3 `"$HooksDir\cursor_hook.py`""
} else {
  "java -jar `"$HooksDir\cursor_hook.jar`""
}
$escaped = $hookCmd -replace '\\','\\\\' -replace '"','\"'
$hooksObj = @{
  version = 1
  hooks = @{
    beforeSubmitPrompt = @(@{ command = $hookCmd })
    stop = @(@{ command = $hookCmd })
  }
}
$hooksJson = $hooksObj | ConvertTo-Json -Depth 4 -Compress
Set-Content -Path "$env:USERPROFILE\.cursor\hooks.json" -Value $hooksJson -Encoding UTF8 -NoNewline

Write-Host "Hook ($(if ($usePython) { 'Python' } else { 'Java' })) installed."
Write-Host "  Collector : $CollectorUrl"
Write-Host "  User      : $(if ($UserEmail) { $UserEmail } else { 'auto (env/git)' })"
Write-Host "  Config    : $HooksDir\hook_config.json"
if (-not $usePython) { Write-Host "  要求      : JRE 11+ (java -version)" }
