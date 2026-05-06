param(
  [switch]$Yes,
  [int]$Port = 8788,
  [string]$RepoUrl = "https://github.com/contentscoin/hermes-for-web-ceo-console.git",
  [switch]$NoStart,
  [switch]$SkipCodex,
  [switch]$SkipTelegram,
  [switch]$SkipPaperclip,
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
  -SkipHermesUpdate do not run hermes update when Hermes CLI already exists
"@
  exit 0
}
function Step($m){ Write-Host "`n==> $m" -ForegroundColor Cyan }
function Has($cmd){ return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Step "Check WSL2"
if(-not (Has wsl)){
  Write-Warning "WSL is not installed. Hermes CEO Console uses WSL2 on Windows for the most reliable runtime."
  Write-Host "Run as Administrator: wsl --install -d Ubuntu"
  Write-Host "Then reboot if Windows asks, open Ubuntu once, and rerun this installer."
  exit 1
}
try { wsl -l -v } catch { Write-Warning "Could not list WSL distros. Open Ubuntu once, finish Linux user setup, then rerun."; exit 1 }

Step "Install/update Hermes runtime inside WSL"
$wizardArgs = @("--port", "$Port", "--repo", "$RepoUrl")
if($Yes){ $wizardArgs += "--yes" }
if($NoStart){ $wizardArgs += "--no-start" }
if($SkipCodex){ $wizardArgs += "--skip-codex" }
if($SkipTelegram){ $wizardArgs += "--skip-telegram" }
if($SkipPaperclip){ $wizardArgs += "--skip-paperclip" }
if($SkipHermesUpdate){ $wizardArgs += "--skip-hermes-update" }
$wizardWin = Join-Path $ScriptDir "scripts\first_run_wizard.py"
$wizardWsl = (wsl wslpath -a ($wizardWin -replace '\\','/')).Trim()
wsl bash -lc "python3 '$wizardWsl' $($wizardArgs -join ' ')"

Step "Create Windows launcher"
$bin = Join-Path $env:USERPROFILE ".hermes\bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
$launcher = Join-Path $bin "hermes-ceo-console-wsl.ps1"
@"
`$ErrorActionPreference = "Stop"
try {
  Invoke-WebRequest -UseBasicParsing http://127.0.0.1:$Port/health -TimeoutSec 2 | Out-Null
} catch {
  Start-Process wsl.exe -ArgumentList "bash -lc 'cd ~/.hermes/webui/workspace/hermes-for-web && ./start.sh $Port >> ~/.hermes/logs/hermes-ceo-console.log 2>&1'" -WindowStyle Hidden
  Start-Sleep -Seconds 3
}
Start-Process "http://127.0.0.1:$Port"
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
try {
  Invoke-RestMethod "http://127.0.0.1:$Port/health" | ConvertTo-Json
} catch {
  Write-Warning "Health check failed. Use the Desktop shortcut or run: $launcher"
}
Write-Host "Done. Shortcut: $shortcutPath"
Write-Host "URL: http://127.0.0.1:$Port"
