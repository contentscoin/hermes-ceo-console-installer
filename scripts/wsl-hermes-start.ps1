param([int]$Port=8788, [string]$Distro="Ubuntu")
$ErrorActionPreference = "Stop"
$Url = "http://127.0.0.1:$Port"
$LogHint = "WSL log: ~/.hermes/logs/hermes-ceo-console.log"

function Test-WebUIHealth {
  try {
    Invoke-WebRequest -UseBasicParsing "$Url/health" -TimeoutSec 2 | Out-Null
    return $true
  } catch {
    return $false
  }
}
function Get-WslDistroNames {
  try {
    $raw = & wsl.exe -l -q 2>$null
    if($LASTEXITCODE -ne 0){ return @() }
    return @($raw | ForEach-Object { ($_ -replace "`0", "").Trim() } | Where-Object { $_ })
  } catch { return @() }
}

if(Test-WebUIHealth){
  Start-Process $Url
  exit 0
}

if(-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)){
  Write-Warning "WSL is not installed, so Hermes CEO Console cannot start the Linux WebUI runtime yet."
  Write-Host "Open PowerShell as Administrator and run: wsl --install -d $Distro"
  Write-Host "After reboot, open $Distro once, create the Linux username/password, then rerun this launcher."
  Read-Host "Press Enter to close"
  exit 1
}

$distros = Get-WslDistroNames
if($distros -notcontains $Distro){
  Write-Warning "WSL distro '$Distro' is not installed, so Hermes CEO Console cannot start the Linux WebUI runtime yet."
  Write-Host "Open PowerShell as Administrator and run: wsl --install -d $Distro"
  Write-Host "If Windows asks, reboot. Then open $Distro once and create the Linux username/password."
  Read-Host "Press Enter to close"
  exit 1
}
try {
  wsl.exe -d $Distro -- bash -lc "printf wsl-ready" | Out-Null
} catch {
  Write-Warning "WSL distro '$Distro' is installed but not initialized yet."
  Write-Host "Open $Distro from the Windows Start menu, create the Linux username/password, then rerun this launcher."
  Read-Host "Press Enter to close"
  exit 1
}

$StartCommand = @'
mkdir -p ~/.hermes/logs
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 >/dev/null
if [ -d ~/.hermes/webui/workspace/paperclip ]; then
  cd ~/.hermes/webui/workspace/paperclip
  nohup pnpm paperclipai run --instance default >> ~/.hermes/logs/paperclip-fmg.log 2>&1 &
fi
cd ~/.hermes/webui/workspace/hermes-for-web
./start.sh __PORT__ >> ~/.hermes/logs/hermes-ceo-console.log 2>&1
'@.Replace('__PORT__', [string]$Port)
Start-Process wsl.exe -ArgumentList @('-d', $Distro, '--', 'bash', '-lc', $StartCommand) -WindowStyle Hidden

for($i=0; $i -lt 30; $i++){
  Start-Sleep -Seconds 1
  if(Test-WebUIHealth){
    Start-Process $Url
    exit 0
  }
}

Write-Warning "Hermes CEO Console WebUI did not become healthy at $Url within 30 seconds. $LogHint"
Start-Process $Url
