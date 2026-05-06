# Hermes CEO Console Installer Pack

Hermes CEO Console Installer Pack은 Hermes Agent, Hermes WebUI, Telegram bot 설정, Paperclip 연결, Codex CLI login을 한 번의 온보딩 흐름으로 묶기 위한 macOS/Windows 설치 패키지입니다.

중요: 이 저장소는 API key, Telegram bot token, Paperclip token, Codex OAuth token을 포함하지 않습니다. 모든 비밀값은 사용자의 로컬 컴퓨터에서 직접 입력하고 `~/.hermes/.env` 또는 각 도구의 로컬 인증 저장소에만 저장됩니다.

## 다운로드

현재 alpha release는 `v0.1.0-alpha.1`입니다. GitHub의 `/releases/download/` 주소는 폴더 페이지가 아니므로, 반드시 아래처럼 `태그명/파일명`까지 포함된 전체 링크로 다운로드하세요.

Release 페이지:
https://github.com/contentscoin/hermes-ceo-console-installer/releases/tag/v0.1.0-alpha.1

직접 다운로드:

- macOS Apple Silicon DMG: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.1/hermes-ceo-console-macos-arm64.dmg
- macOS DMG checksum: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.1/hermes-ceo-console-macos-arm64.dmg.sha256
- Windows EXE: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.1/Hermes.CEO.Console.Setup.0.1.0-alpha.1.exe
- Windows EXE checksum: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.1/windows-exe.sha256
- Script installer pack: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.1/hermes-ceo-console-installer-pack.zip
- Script installer pack checksum: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.1/hermes-ceo-console-installer-pack.zip.sha256

터미널에서 macOS DMG를 바로 받으려면:

```bash
curl -L -o ~/Downloads/hermes-ceo-console-macos-arm64.dmg https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.1/hermes-ceo-console-macos-arm64.dmg
```

Release 자동 빌드가 아직 끝나지 않았거나 alpha 테스트 중이면 zip pack을 받아 아래 스크립트 방식으로 설치하세요.

## 설치 목표

설치 후 사용자는 다음 흐름을 갖게 됩니다.

1. 데스크톱 앱 또는 바로가기로 Hermes CEO Console 실행
2. 내부 WebUI는 `http://127.0.0.1:8788` 에서 실행
3. Hermes Agent 설치/업데이트 확인
4. Hermes WebUI 설치/업데이트 확인
5. Codex CLI 설치 및 `codex login` 안내
6. Telegram bot token 설정 안내
7. Paperclip URL/company/token 설정 안내
8. `hermes doctor` 및 WebUI health check

## macOS 설치

### 방법 A: DMG

1. Release에서 `Hermes CEO Console-*.dmg` 다운로드
2. 앱을 Applications로 이동
3. 앱 실행
4. Setup 화면이 나오면 `Run Setup Wizard` 클릭

### 방법 B: script pack

```bash
curl -L -o hermes-ceo-console-installer-pack.zip https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.1/hermes-ceo-console-installer-pack.zip
unzip hermes-ceo-console-installer-pack.zip -d hermes-ceo-console-installer
cd hermes-ceo-console-installer
chmod +x install-macos.sh scripts/first_run_wizard.py
./install-macos.sh
```

비밀값 입력 없이 기본 설치만 먼저 하려면:

```bash
./install-macos.sh --yes --skip-telegram --skip-paperclip --skip-codex
```

설치 후 URL:

```text
http://127.0.0.1:8788
```

## Windows 설치

권장 방식은 WSL2 런타임입니다. Windows 앱은 데스크톱 앱처럼 작동하고, Hermes/Hermes WebUI는 WSL2 Ubuntu 안에서 실행됩니다.

### 방법 A: EXE

1. Release에서 `Hermes CEO Console Setup *.exe` 다운로드
2. 설치 실행
3. 앱에서 `처음 설치 / Setup Wizard`를 누르면 별도 PowerShell 창이 열립니다.
4. WSL2가 없으면 안내에 따라 설치
5. PowerShell Setup Wizard에서 Hermes, Codex, Telegram, Paperclip 설정

주의: Setup Wizard는 Codex login, Telegram token, Paperclip 값처럼 사용자가 직접 입력해야 하는 단계가 있으므로 앱 내부의 숨은 백그라운드가 아니라 눈에 보이는 명령 프롬프트/PowerShell 창에서 진행됩니다. 버튼을 눌렀는데 화면이 바뀌지 않으면 Windows 작업표시줄의 새 창이나 보안 경고 창을 먼저 확인하세요. 그래도 아무 창이 열리지 않으면 앱 화면에 표시되는 `run-hermes-ceo-console-setup.cmd` 파일 경로를 직접 더블클릭하세요. 예전 빌드에서 `Hermes CEO Console Setup을 찾을 수 없습니다` 오류가 뜬 경우 최신 EXE를 다시 다운로드해 설치하세요.

### 방법 B: PowerShell script pack

PowerShell을 열고:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
Invoke-WebRequest -Uri "https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.1/hermes-ceo-console-installer-pack.zip" -OutFile "hermes-ceo-console-installer-pack.zip"
Expand-Archive .\hermes-ceo-console-installer-pack.zip -DestinationPath .\hermes-ceo-console-installer -Force
cd .\hermes-ceo-console-installer
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

WSL2가 없다면 관리자 PowerShell에서 먼저:

```powershell
wsl --install -d Ubuntu
```

그 뒤 Windows 재시작 또는 Ubuntu 첫 실행을 완료하고 installer를 다시 실행하세요. Windows 설치가 중간에 멈추거나 바로 닫히면 대부분 아래 2가지 중 하나입니다.

```powershell
wsl -l -v
wsl bash -lc "python3 --version && git --version && curl --version"
```

- `wsl bash`가 실패하면 Ubuntu를 한 번 직접 열어 Linux username/password 초기화를 끝낸 뒤 다시 실행하세요.
- `python3`, `git`, `curl` 중 하나가 없으면 최신 installer가 WSL 안에서 자동 설치를 시도합니다. 수동으로는 `wsl bash -lc "sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip git curl ca-certificates"`를 실행하면 됩니다.

## Codex CLI login

Codex CLI login은 자동으로 끝낼 수 없습니다. 설치 마법사가 `codex login`을 실행하거나 안내하면 브라우저/OAuth/device flow를 사용자가 직접 승인해야 합니다.

설치 후 직접 실행:

```bash
codex --version
codex login
```

Windows WSL2 모드에서는 WSL 안에서 실행하세요.

```powershell
wsl bash -lc "codex --version && codex login"
```

## Telegram bot setup

Telegram bot token은 BotFather에서 생성해야 합니다.

1. https://t.me/BotFather 열기
2. `/newbot` 실행
3. bot 이름/username 지정
4. token을 복사
5. setup wizard에 붙여넣기

주의:
- token은 화면에 다시 출력하지 않습니다.
- token은 repo에 저장하지 않습니다.
- 실제 Telegram 메시지 전송은 항상 대상/문구 승인 후 진행해야 합니다.

## Paperclip setup

필요한 값:

- `PAPERCLIP_WEB_URL` — WebUI 상단 Paperclip 탭에 embed되는 실제 Paperclip 작업 화면 URL. 기본값은 `http://127.0.0.1:3100` 입니다.
- `PAPERCLIP_BASE_URL` — MCP/API 작업용 Paperclip base URL
- `PAPERCLIP_DEFAULT_COMPANY`
- 필요한 경우 `PAPERCLIP_API_TOKEN`

설정 위치:

```text
~/.hermes/.env
```

원칙:
- 설치 프로그램은 Paperclip 연결 정보를 설정/점검할 수 있습니다.
- Paperclip issue/comment/status update는 자동 실행하지 않습니다.
- Decision Report / dry-run preview 후 명시 승인 시에만 반영해야 합니다.

## Hermes setup

처음 사용하는 사용자는 설치 후 다음을 실행하세요.

```bash
hermes setup
hermes doctor
```

Telegram gateway를 쓰려면:

```bash
hermes gateway setup
hermes gateway run
```

또는 OS 서비스 설치:

```bash
hermes gateway install
hermes gateway start
```

## 포함 파일

```text
install-macos.sh
install-windows.ps1
installer.manifest.json
scripts/first_run_wizard.py
scripts/install-wsl-runtime.ps1
scripts/wsl-hermes-start.ps1
templates/.env.example
profiles/fmg.profile.json
electron-wrapper/
.github/workflows/release.yml
```

## 개발자 빌드

### macOS DMG

```bash
cd electron-wrapper
npm install
npm run build:mac
```

결과:

```text
electron-wrapper/dist/*.dmg
```

### Windows EXE

Windows 또는 GitHub Actions Windows runner에서:

```powershell
cd electron-wrapper
npm install
npm run build:win
```

결과:

```text
electron-wrapper/dist/*.exe
```

### Script installer zip

```bash
zip -r hermes-ceo-console-installer-pack.zip install-macos.sh install-windows.ps1 scripts templates profiles installer.manifest.json README.md LICENSE
```

## 보안 원칙

- 이 repo에는 secret이 없습니다.
- `.env`, token, OAuth cache, API key는 commit하지 않습니다.
- setup wizard는 secret 값을 다시 출력하지 않습니다.
- Paperclip 반영과 Telegram 전송은 설치 완료 후에도 승인 게이트를 유지해야 합니다.

## 문제 해결

### WebUI가 열리지 않음

```bash
curl http://127.0.0.1:8788/health
```

macOS log:

```bash
tail -100 ~/.hermes/logs/hermes-ceo-console.log
```

Windows WSL log:

```powershell
wsl bash -lc "tail -100 ~/.hermes/logs/hermes-ceo-console.log"
```

### Hermes가 없음

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes setup
```

### Windows에서 WSL 연결 안 됨

```powershell
wsl -l -v
wsl --install -d Ubuntu
```

## 현재 상태

Alpha installer pack입니다.

지원:
- macOS script installer
- Windows WSL2-first script installer
- Electron wrapper skeleton
- GitHub Actions build workflow
- Secret-free FMG profile

다음 단계:
- Apple Developer ID signing/notarization
- Windows code signing
- auto-update
- richer in-app setup status
