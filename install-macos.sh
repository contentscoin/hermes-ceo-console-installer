#!/usr/bin/env bash
set -euo pipefail
PORT=8788
REPO="https://github.com/contentscoin/hermes-for-web-ceo-console.git"
INSTALL_DIR="$HOME/.hermes/webui/workspace/hermes-for-web"
YES=0
NO_START=0
SKIP_CODEX=0
SKIP_TELEGRAM=0
SKIP_PAPERCLIP=0
SKIP_HERMES_UPDATE=0
APP_NAME="Hermes CEO Console"

usage(){ cat <<EOF
Hermes CEO Console macOS installer

Usage: ./install-macos.sh [options]
  --yes, -y             non-interactive defaults; does not fill secrets
  --port PORT           default: 8788
  --repo URL            WebUI repo URL
  --dir PATH            install directory
  --skip-codex          skip Codex login step
  --skip-telegram       skip Telegram token prompt
  --skip-paperclip      skip Paperclip prompt
  --skip-hermes-update  do not run hermes update when Hermes CLI already exists
  --no-start            install only; do not start WebUI
  --help                show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes|-y) YES=1; shift;;
    --port) PORT="${2:?}"; shift 2;;
    --repo) REPO="${2:?}"; shift 2;;
    --dir) INSTALL_DIR="${2:?}"; shift 2;;
    --skip-codex) SKIP_CODEX=1; shift;;
    --skip-telegram) SKIP_TELEGRAM=1; shift;;
    --skip-paperclip) SKIP_PAPERCLIP=1; shift;;
    --skip-hermes-update) SKIP_HERMES_UPDATE=1; shift;;
    --no-start) NO_START=1; shift;;
    --help|-h) usage; exit 0;;
    *) echo "Unknown argument: $1"; usage; exit 2;;
  esac
done

step(){ printf '\n==> %s\n' "$1"; }
need_or_hint(){
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing: $1"
    if [[ "$1" == "git" ]]; then echo "Install Apple Command Line Tools: xcode-select --install"; fi
    return 1
  fi
}

step "Prerequisites"
need_or_hint curl
need_or_hint python3
need_or_hint git

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIZARD="$SCRIPT_DIR/scripts/first_run_wizard.py"
chmod +x "$WIZARD"

step "Run first-run wizard"
args=("$WIZARD" --port "$PORT" --repo "$REPO" --install-dir "$INSTALL_DIR")
[[ "$YES" == 1 ]] && args+=(--yes)
[[ "$NO_START" == 1 ]] && args+=(--no-start)
[[ "$SKIP_CODEX" == 1 ]] && args+=(--skip-codex)
[[ "$SKIP_TELEGRAM" == 1 ]] && args+=(--skip-telegram)
[[ "$SKIP_PAPERCLIP" == 1 ]] && args+=(--skip-paperclip)
[[ "$SKIP_HERMES_UPDATE" == 1 ]] && args+=(--skip-hermes-update)
python3 "${args[@]}"

step "Create macOS app launcher"
APP_DIR="$HOME/Applications/$APP_NAME.app"
if [[ -f "$APP_DIR/Contents/Resources/app.asar" || -f "$APP_DIR/Contents/MacOS/$APP_NAME" ]]; then
  APP_DIR="$HOME/Applications/$APP_NAME Web Launcher.app"
fi
mkdir -p "$APP_DIR/Contents/MacOS"
cat > "$APP_DIR/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundleIdentifier</key><string>com.fmg.hermes-ceo-console</string>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundlePackageType</key><string>APPL</string>
</dict></plist>
PLIST
cat > "$APP_DIR/Contents/MacOS/launcher" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$INSTALL_DIR"
if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  open "http://127.0.0.1:$PORT"
  exit 0
fi
./start.sh "$PORT" > "\$HOME/.hermes/logs/hermes-ceo-console.log" 2>&1 &
sleep 2
open "http://127.0.0.1:$PORT"
EOF
chmod +x "$APP_DIR/Contents/MacOS/launcher"

echo "Done. App launcher: $APP_DIR"
echo "URL: http://127.0.0.1:$PORT"
