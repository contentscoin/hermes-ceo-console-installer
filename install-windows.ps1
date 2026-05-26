param(
  [switch]$Yes,
  [int]$Port = 8788,
  [string]$RepoUrl = "https://github.com/contentscoin/hermes-for-web.git",
  [string]$RepoRef = "main",
  [string]$ExpectedWebUICommit = "e3e593dc2dc526dedcd8fa0b66ed13f858d65b09",
  [string]$PaperclipRepoUrl = "https://github.com/paperclipai/paperclip.git",
  [string]$PaperclipRepoRef = "master",
  [string]$ExpectedPaperclipCommit = "9aea3e3d35fe47a745857b91c392da5b3fc0ae17",
  [int]$PaperclipPort = 3100,
  [string]$Distro = "Ubuntu",
  [switch]$NoStart,
  [switch]$SkipCodex,
  [switch]$SkipTelegram,
  [switch]$SkipPaperclip,
  [switch]$SkipOpenCrab,
  [switch]$SkipNeo4j,
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
  -RepoRef main     WebUI repo ref/branch
  -ExpectedWebUICommit SHA  expected FMG WebUI commit
  -Distro Ubuntu    WSL Linux distro to install/use
  -PaperclipRepoUrl URL       FMG Paperclip repo URL
  -PaperclipRepoRef REF       FMG Paperclip branch/ref
  -ExpectedPaperclipCommit SHA expected FMG Paperclip commit
  -PaperclipPort 3100         Paperclip local port
  -NoStart          install only
  -SkipCodex        skip Codex login step
  -SkipTelegram     skip Telegram token prompt
  -SkipPaperclip    skip Paperclip prompt
  -SkipOpenCrab     skip OpenCrab MCP prompt
  -SkipNeo4j        skip Neo4j optional config/readiness check
  -SkipHermesUpdate do not run hermes update when Hermes CLI already exists
                    The wizard targets Hermes Agent v0.14.0 and prints source commits too.
"@
  exit 0
}
function Step($m){ Write-Host "`n==> $m" -ForegroundColor Cyan }
function Has($cmd){ return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Quote-BashArg([string]$s){ return "'" + ($s.Replace("'", "'`"'`"'")) + "'" }
function Guide($m){ Write-Host "  -> $m" -ForegroundColor Yellow }
function Test-Administrator {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Get-WslDistroNames {
  try {
    $raw = & wsl.exe -l -q 2>$null
    if($LASTEXITCODE -ne 0){ return @() }
    return @($raw | ForEach-Object { ($_ -replace "`0", "").Trim() } | Where-Object { $_ })
  } catch {
    return @()
  }
}
function Install-WslDistroIfNeeded([string]$Name){
  if(-not (Has wsl.exe)){
    Write-Warning "wsl.exe is not available on this Windows installation."
    if(Test-Administrator){
      Write-Host "Enabling Windows optional features for WSL2..."
      dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
      dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
      Write-Warning "WSL Windows features were enabled. Reboot Windows, then rerun this installer."
    } else {
      Write-Host "Open PowerShell as Administrator and run: wsl --install -d $Name"
    }
    exit 1
  }

  $distros = Get-WslDistroNames
  if($distros -contains $Name){ return }

  Write-Warning "No '$Name' WSL Linux distribution is installed yet. Installing it now."
  Write-Host "This may require Administrator permission, Microsoft Store access, and/or a Windows reboot."
  try {
    & wsl.exe --install -d $Name
  } catch {
    Write-Warning "wsl --install -d $Name failed. Trying web-download fallback."
    try { & wsl.exe --install --web-download -d $Name } catch {}
  }

  $distros = Get-WslDistroNames
  if($distros -notcontains $Name){
    Write-Warning "The '$Name' WSL distribution is still not listed after install attempt."
    Write-Host "If Windows requested a reboot, reboot first. Otherwise run as Administrator: wsl --install -d $Name"
    Write-Host "After install, open $Name once and create the Linux username/password, then rerun this installer."
    exit 1
  }

  Write-Warning "'$Name' is installed but may still need first-run initialization."
  Write-Host "If a $Name terminal opens, create the Linux username/password. Then rerun this installer if it stops here."
}
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Step "Check WSL2 and Linux distro"
Guide "Stage 1/4: checking Windows WSL and the $Distro Linux distribution."
Guide "If $Distro was just installed, Windows may ask you to reboot or open $Distro once to create a Linux username/password."
Guide "After that, pressing Setup Wizard again is expected; it continues to the Hermes runtime install."
Install-WslDistroIfNeeded $Distro
try { wsl -l -v } catch { Write-Warning "Could not list WSL distros. Open $Distro once, finish Linux user setup, then rerun."; exit 1 }
try {
  wsl -d $Distro -- bash -lc "printf wsl-ready" | Out-Null
} catch {
  Write-Warning "WSL distro '$Distro' is installed, but it is not initialized or not ready yet."
  Write-Host "Open $Distro from the Windows Start menu, create the Linux username/password, then rerun this installer."
  exit 1
}

Step "Check WSL prerequisites"
Guide "Stage 2/4: checking python3, git, and curl inside $Distro. You may be asked for the Ubuntu password for sudo."
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
wsl -d $Distro -- bash -lc $bootstrap

Step "Install/update Hermes runtime inside WSL"
Guide "Stage 3/4: checking/updating Hermes Agent, FMG WebUI, and FMG-customized Paperclip inside $Distro."
Guide "This is the step you saw after pressing Setup again. It is normal after Ubuntu is ready."
Guide "Keep this PowerShell window open until it prints Done. First install can take several minutes."
Guide "Quick setup skips Codex/Telegram secret prompts, but installs/starts FMG-customized Paperclip locally."
Guide "Hermes Agent target is v0.14.0; the wizard also prints Hermes source, WebUI, and Paperclip commits."
$wizardArgs = @("--port", "$Port", "--repo", "$RepoUrl", "--repo-ref", "$RepoRef", "--expected-webui-commit", "$ExpectedWebUICommit", "--paperclip-repo", "$PaperclipRepoUrl", "--paperclip-repo-ref", "$PaperclipRepoRef", "--expected-paperclip-commit", "$ExpectedPaperclipCommit", "--paperclip-port", "$PaperclipPort")
if($Yes){ $wizardArgs += "--yes" }
if($NoStart){ $wizardArgs += "--no-start" }
if($SkipCodex){ $wizardArgs += "--skip-codex" }
if($SkipTelegram){ $wizardArgs += "--skip-telegram" }
if($SkipPaperclip){ $wizardArgs += "--skip-paperclip" }
if($SkipOpenCrab){ $wizardArgs += "--skip-opencrab" }
if($SkipNeo4j){ $wizardArgs += "--skip-neo4j" }
if($SkipHermesUpdate){ $wizardArgs += "--skip-hermes-update" }
$wizardWin = Join-Path $ScriptDir "scripts\first_run_wizard.py"
$wizardWsl = (wsl -d $Distro -- wslpath -a ($wizardWin -replace '\\','/')).Trim()
$quotedArgs = ($wizardArgs | ForEach-Object { Quote-BashArg $_ }) -join ' '
wsl -d $Distro -- bash -lc "python3 $(Quote-BashArg $wizardWsl) $quotedArgs"

Step "Create Windows launcher"
$bin = Join-Path $env:USERPROFILE ".hermes\bin"
New-Item -ItemType Directory -Force -Path $bin | Out-Null
$launcher = Join-Path $bin "hermes-ceo-console-wsl.ps1"
@"
`$ErrorActionPreference = "Stop"
`$Url = "http://127.0.0.1:$Port"
`$Distro = "$Distro"
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
  Write-Host "Open PowerShell as Administrator and run: wsl --install -d `$Distro"
  Write-Host "After reboot, open `$Distro once, create the Linux username/password, then rerun this launcher."
  Read-Host "Press Enter to close"
  exit 1
}
function Get-WslDistroNames {
  try {
    `$raw = & wsl.exe -l -q 2>`$null
    if(`$LASTEXITCODE -ne 0){ return @() }
    return @(`$raw | ForEach-Object { (`$_ -replace "``0", "").Trim() } | Where-Object { `$_ })
  } catch { return @() }
}
`$distros = Get-WslDistroNames
if(`$distros -notcontains `$Distro){
  Write-Warning "WSL distro '`$Distro' is not installed, so Hermes CEO Console cannot start the Linux WebUI runtime yet."
  Write-Host "Open PowerShell as Administrator and run: wsl --install -d `$Distro"
  Write-Host "If Windows asks, reboot. Then open `$Distro once and create the Linux username/password."
  Read-Host "Press Enter to close"
  exit 1
}
try { wsl.exe -d `$Distro -- bash -lc "printf wsl-ready" | Out-Null } catch {
  Write-Warning "WSL distro '`$Distro' is installed but not initialized yet."
  Write-Host "Open `$Distro from the Windows Start menu, create the Linux username/password, then rerun this launcher."
  Read-Host "Press Enter to close"
  exit 1
}
`$StartCommand = @'
mkdir -p ~/.hermes/logs
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 >/dev/null
if [ -d ~/.hermes/webui/workspace/paperclip ]; then
  cd ~/.hermes/webui/workspace/paperclip
  nohup pnpm paperclipai run --instance default >> ~/.hermes/logs/paperclip-fmg.log 2>&1 &
fi
cd ~/.hermes/webui/workspace/hermes-for-web
./start.sh $Port >> ~/.hermes/logs/hermes-ceo-console.log 2>&1
'@
Start-Process wsl.exe -ArgumentList @('-d', `$Distro, '--', 'bash', '-lc', `$StartCommand) -WindowStyle Hidden
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
Guide "Stage 4/4: starting WebUI and checking http://127.0.0.1:$Port/health from Windows."
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
