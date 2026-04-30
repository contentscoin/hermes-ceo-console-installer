param([string]$Distro="Ubuntu")
$ErrorActionPreference = "Stop"
if(-not (Get-Command wsl -ErrorAction SilentlyContinue)){
  Write-Host "Installing WSL2 with $Distro. You may need Administrator privileges and a reboot."
  wsl --install -d $Distro
} else {
  wsl -l -v
  Write-Host "WSL is already available. If no distro is initialized, run: wsl --install -d $Distro"
}
