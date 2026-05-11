param([string]$Distro="Ubuntu")
$ErrorActionPreference = "Stop"

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

if(-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)){
  Write-Warning "wsl.exe is not available yet. Hermes CEO Console needs WSL2 plus a Linux distro such as $Distro."
  if(Test-Administrator){
    Write-Host "Enabling Windows optional features for WSL2..."
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    Write-Warning "WSL Windows features were enabled. Reboot Windows, then rerun this script."
  } else {
    Write-Host "Open PowerShell as Administrator and run: wsl --install -d $Distro"
  }
  exit 1
}

$distros = Get-WslDistroNames
if($distros -contains $Distro){
  Write-Host "WSL distro '$Distro' is already installed."
  wsl.exe -l -v
  try {
    wsl.exe -d $Distro -- bash -lc "printf wsl-ready" | Out-Null
    Write-Host "WSL distro '$Distro' is initialized and ready."
    exit 0
  } catch {
    Write-Warning "WSL distro '$Distro' is installed but not initialized."
    Write-Host "Open $Distro from the Windows Start menu, create the Linux username/password, then rerun."
    exit 1
  }
}

Write-Host "Installing WSL2 distro '$Distro'. You may need Administrator privileges and a reboot."
try {
  wsl.exe --install -d $Distro
} catch {
  Write-Warning "wsl --install -d $Distro failed. Trying web-download fallback."
  wsl.exe --install --web-download -d $Distro
}

$distros = Get-WslDistroNames
if($distros -contains $Distro){
  Write-Warning "'$Distro' is installed. Open it once, create the Linux username/password, then rerun the Hermes CEO Console installer."
  exit 0
}

Write-Warning "'$Distro' is still not listed. If Windows requested a reboot, reboot first. Otherwise run as Administrator: wsl --install -d $Distro"
exit 1
