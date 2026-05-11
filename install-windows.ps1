param(
  [switch]$Yes,
  [int]$Port = 8788,
  [string]$RepoUrl = "https://github.com/contentscoin/hermes-for-web.git",
  [switch]$NoStart,
  [switch]$SkipCodex,
  [switch]$SkipTelegram,
  [switch]$SkipPaperclip,
  [switch]$SkipOpenCrab,
  [switch]$SkipHermesUpdate,
  [switch]$Help
)
$ErrorActionPreference = "Stop"
if($Help){
  Write-Host @"
Hermes CEO Console Windows installer (WSL2 runtime recommended)

Usage: powershell -ExecutionPolicy Bypass -File .\install-windows.ps1 [options]
  -Yes              non-interactive defaults; does not fill secrets
  -Port 8788        WebUI port
  -RepoUrl URL      WebUI repo URL
  -NoStart          install only
  -SkipCodex        skip Codex login step
  -SkipTelegram     skip Telegram token prompt
  -SkipPaperclip    skip Paperclip prompt
  -SkipOpenCrab     skip OpenCrab MCP prompt
  -SkipHermesUpdate do not run hermes update when Hermes CLI already exists
"@
  exit 0
}
function Step($m){ Write-Host "`n==> $m" -ForegroundColor Cyan }
function Has($cmd){ return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Quote-BashArg([string]$s){ return "'" + ($s.Replace("'", "'`"'`"'")) + "'" }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Step "Check WSL2"
if(-not (Has wsl)){
  Write-Warning "WSL is not installed. Hermes CEO Console uses WSL2 on Windows for the most reliable runtime."
  Write-Host "Run as Administrator: wsl --install -d Ubuntu"
  Write-Host "Then reboot if Windows asks, open Ubuntu once, and rerun this installer."
  exit 1
}
try { wsl -l -v } catch { Write-Warning "Could not list WSL distros. Open Ubuntu once, finish Linux user setup, then rerun."; exit 1 }
try {
  wsl bash -lc "printf wsl-ready" | Out-Null
} catch {
  Write-Warning "WSL is installed, but the default Linux distro is not ready."
  Write-Host "Open Ubuntu once, finish the Linux username/password setup, then rerun this installer."
  exit 1
}

Step "Check WSL prerequisites"
$bootstrap = @'
set -e
missing=""
for cmd in python3 git curl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then missing="$missing $cmd"; fi
done
if [ -n "$missing" ]; then
  echo "Installing WSL prerequisites:$missing"
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip git curl ca-certificates
  else
    echo "Missing required commands:$missing"
    echo "Please install python3, git, and curl inside your WSL distro, then rerun."
    exit 1
  fi
fi
'@
wsl bash -lc $bootstrap

Step "Install/update Hermes runtime inside WSL"
$wizardArgs = @("--port", "$Port", "--repo", "$RepoUrl")
if($Yes){ $wizardArgs += "--yes" }
if($NoStart){ $wizardArgs += "--no-start" }
if($SkipCodex){ $wizardArgs += "--skip-codex" }
if($SkipTelegram){ $wizardArgs += "--skip-telegram" }
if($SkipPaperclip){ $wizardArgs += "--skip-paperclip" }
if($SkipOpenCrab){ $wizardArgs += "--skip-opencrab" }
if($SkipHermesUpdate){ $wizardArgs += "--skip-hermes-update" }
$wizardWin = Join-Path $ScriptDir "scripts\first_run_wizard.py"
$wizardWsl = (wsl wslpath -a ($wizardWin -replace '\\','/')).Trim()
$quotedArgs = ($wizardArgs | ForEach-Object { Quote-BashArg $_ }) -join ' '
wsl bash -lc "python3 $(Quote-BashArg $wizardWsl) $quotedArgs"

Step "Create Windows launcher"
$bin = Join-Path $env:USERPROFILE ".hermes\bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
$launcher = Join-Path $bin "hermes-ceo-console-wsl.ps1"
@"
`$ErrorActionPreference = "Stop"
`$Url = "http://127.0.0.1:$Port"
function Test-WebUIHealth {
  try {
    Invoke-WebRequest -UseBasicParsing "`$Url/health" -TimeoutSec 2 | Out-Null
    return `$true
  } catch {
    return `$false
  }
}
if(Test-WebUIHealth){
  Start-Process `$Url
  exit 0
}
if(-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)){
  Write-Warning "WSL is not installed, so Hermes CEO Console cannot start the Linux WebUI runtime yet."
  Write-Host "Open PowerShell as Administrator and run: wsl --install -d Ubuntu"
  Write-Host "After reboot, open Ubuntu once, create the Linux username/password, then rerun this launcher."
  Read-Host "Press Enter to close"
  exit 1
}
Start-Process wsl.exe -ArgumentList "bash -lc 'mkdir -p ~/.hermes/logs; cd ~/.hermes/webui/workspace/hermes-for-web && ./start.sh $Port >> ~/.hermes/logs/hermes-ceo-console.log 2>&1'" -WindowStyle Hidden
for(`$i=0; `$i -lt 30; `$i++){
  Start-Sleep -Seconds 1
  if(Test-WebUIHealth){
    Start-Process `$Url
    exit 0
  }
}
Write-Warning "Hermes CEO Console WebUI did not become healthy at `$Url within 30 seconds. WSL log: ~/.hermes/logs/hermes-ceo-console.log"
Start-Process `$Url
"@ | Set-Content -Encoding UTF8 $launcher

$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop "Hermes CEO Console.lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$launcher`""
$shortcut.WorkingDirectory = $bin
$shortcut.IconLocation = "powershell.exe,0"
$shortcut.Save()

Step "Verify WebUI from Windows"
$healthy = $false
for($i=0; $i -lt 30; $i++){
  try {
    Invoke-RestMethod "http://127.0.0.1:$Port/health" | ConvertTo-Json
    $healthy = $true
    break
  } catch {
    Start-Sleep -Seconds 1
  }
}
if(-not $healthy){
  Write-Warning "Health check failed after waiting. Use the Desktop shortcut or run: $launcher"
  Write-Host "If it still does not open, check WSL log inside Ubuntu: tail -80 ~/.hermes/logs/hermes-ceo-console.log"
}
Write-Host "Done. Shortcut: $shortcutPath"
Write-Host "URL: http://127.0.0.1:$Port"
