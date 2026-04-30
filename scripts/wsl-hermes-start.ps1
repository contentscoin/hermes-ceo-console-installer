param([int]$Port=8788)
$ErrorActionPreference = "Stop"
try { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/health" -TimeoutSec 2 | Out-Null; Start-Process "http://127.0.0.1:$Port"; exit 0 } catch {}
wsl bash -lc "mkdir -p ~/.hermes/logs; cd ~/.hermes/webui/workspace/hermes-for-web && ./start.sh $Port >> ~/.hermes/logs/hermes-ceo-console.log 2>&1"
Start-Process "http://127.0.0.1:$Port"
