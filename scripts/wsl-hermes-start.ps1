param([int]$Port=8788)
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

if(Test-WebUIHealth){
  Start-Process $Url
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

for($i=0; $i -lt 30; $i++){
  Start-Sleep -Seconds 1
  if(Test-WebUIHealth){
    Start-Process $Url
    exit 0
  }
}

Write-Warning "Hermes CEO Console WebUI did not become healthy at $Url within 30 seconds. $LogHint"
Start-Process $Url
