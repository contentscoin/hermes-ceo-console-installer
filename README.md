# Hermes CEO Console Installer Pack

Hermes CEO Console Installer Pack은 FMG용 Hermes Agent, FMG 커스터마이징 Hermes WebUI, FMG 커스터마이징 Paperclip, Telegram, Codex CLI, OpenCrab 선택 설정을 하나의 온보딩 흐름으로 묶는 macOS/Windows 설치 패키지입니다.

이 installer의 목표는 사용자가 데스크톱 앱처럼 Hermes CEO Console을 실행하면 내부적으로 다음 로컬 서비스가 준비되는 것입니다.

- Hermes WebUI: http://127.0.0.1:8788
- FMG Paperclip: http://127.0.0.1:3100
- Hermes Agent CLI: `hermes`
- 선택 통합: Telegram gateway, Codex CLI, OpenCrab MCP

중요: 이 저장소는 API key, Telegram bot token, Paperclip token, Codex OAuth token, OpenCrab endpoint key를 포함하지 않습니다. 모든 비밀값은 사용자의 로컬 컴퓨터에서 직접 입력하고 `~/.hermes/.env`, `~/.hermes/config.yaml`, 또는 각 도구의 로컬 인증 저장소에만 저장됩니다.

---

## 1. 현재 릴리스

현재 alpha release는 `v0.1.0-alpha.17`입니다.

Release 페이지:
https://github.com/contentscoin/hermes-ceo-console-installer/releases/latest

직접 다운로드:

- Windows EXE: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/Hermes.CEO.Console.Setup.0.1.0-alpha.17.exe
- Windows EXE checksum: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/windows-exe.sha256
- macOS Apple Silicon DMG: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/hermes-ceo-console-macos-arm64.dmg
- macOS DMG checksum: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/hermes-ceo-console-macos-arm64.dmg.sha256
- Script installer pack: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/hermes-ceo-console-installer-pack.zip
- Script installer pack checksum: https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/hermes-ceo-console-installer-pack.zip.sha256

GitHub의 `/releases/download/` 주소는 폴더 페이지가 아닙니다. 반드시 `태그명/파일명`까지 포함된 전체 링크를 사용하세요.

---

## 2. 출처 및 오픈소스 고지

이 저장소는 FMG가 Hermes CEO Console 배포를 위해 만든 installer/wrapper 저장소입니다. 아래 upstream 프로젝트와 서비스 위에 구성되며, 각 프로젝트의 라이선스와 상표권은 원 저작자에게 있습니다. 이 저장소는 해당 프로젝트들의 공식 배포 채널이 아니라 FMG용 통합 설치/온보딩 패키지입니다.

| 구분 | 출처 / 원 프로젝트 | 이 installer에서의 사용 범위 |
| --- | --- | --- |
| Hermes Agent | Nous Research, `https://github.com/NousResearch/hermes-agent` | 로컬 AI agent CLI/runtime 설치 및 실행 |
| Hermes WebUI | FMG fork `https://github.com/contentscoin/hermes-for-web.git`; upstream 기반 WebUI | CEO Console 화면, multi-agent/profile/workspace/Paperclip/OpenCrab 연동 UI |
| Paperclip | Paperclip project / FMG fork `https://github.com/contentscoin/paperclip.git` | 로컬 FMG Paperclip 보드와 read-only workflow diagnostics / iframe 연동 |
| OpenCrab | OpenCrab service, `https://opencrab.sh` | 사용자가 직접 설정한 MCP endpoint를 통한 선택형 ontology connector 상태 확인. endpoint key는 포함하지 않음 |
| Desktop wrapper | Electron / electron-builder 생태계 | macOS DMG 및 Windows NSIS installer shell 빌드 |
| Node / pnpm / WSL2 / Ubuntu | 각 배포 프로젝트 및 Microsoft/Ubuntu 생태계 | Windows WSL2 기반 runtime 설치와 dependency bootstrap |

비밀값/인증 정보 고지:
- 이 저장소와 release asset에는 API key, Telegram bot token, Codex OAuth token, Paperclip token, OpenCrab endpoint key가 포함되지 않습니다.
- OpenCrab endpoint는 항상 `https://opencrab.sh/api/mcp/[REDACTED]` 형태로만 표시해야 합니다.
- Paperclip reflection, Telegram 전송, OpenCrab ingest/sync, Neo4j write는 installer가 자동 수행하지 않으며 별도 사용자 승인 대상입니다.

자세한 attribution/NOTICE는 `NOTICE.md`를 함께 확인하세요.

---

## 3. 설치 후 구성

설치가 정상 완료되면 아래 구조가 됩니다.

```text
~/.hermes/
  .env                         # 로컬 secret/env 설정
  config.yaml                  # Hermes 설정, MCP 설정
  logs/
    hermes-ceo-console.log     # WebUI 실행 로그
    paperclip-fmg.log          # Paperclip 실행 로그
  webui/workspace/
    hermes-for-web/            # FMG Hermes WebUI
    paperclip/                 # FMG Paperclip
```

기본 포트:

```text
Hermes WebUI     http://127.0.0.1:8788
Paperclip        http://127.0.0.1:3100
Paperclip health http://127.0.0.1:3100/api/health
WebUI health     http://127.0.0.1:8788/health
```

FMG 소스 고정값:

```text
Hermes WebUI repo      https://github.com/contentscoin/hermes-for-web.git
Hermes WebUI ref       main
Hermes WebUI commit    d6cf50a59b34b3a5534d96cf9732a6a2523413dd

Paperclip repo         https://github.com/contentscoin/paperclip.git
Paperclip ref          live/opencrab-default-dag-20260510
Paperclip commit       72bb0505a09d5b789a8a88c6cbd26c024b2e4215
```

Hermes Agent 기준값:

```text
Hermes Agent repo      https://github.com/NousResearch/hermes-agent.git
Hermes Agent version   v0.14.0 (2026.5.16)
Hermes Agent commit    973f27e95631aaecbda5e32e3fa9e5d7f6a2e1d3
```

중요: FMG 커스터마이징 설치 여부는 `hermes --version`만이 아니라 `hermes-agent`, `hermes-for-web`, `paperclip`의 git remote/commit으로 함께 확인해야 합니다.

---

## 4. Windows 설치 방법

Windows 권장 방식은 WSL2 + Ubuntu 런타임입니다. Windows 앱은 데스크톱 shell처럼 작동하고, Hermes Agent / Hermes WebUI / Paperclip은 Ubuntu 안에서 실행됩니다.

### 4.1 가장 쉬운 설치: Windows EXE

1. 아래 EXE를 다운로드합니다.

```text
https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/Hermes.CEO.Console.Setup.0.1.0-alpha.17.exe
```

2. EXE를 실행해 설치합니다.
3. Hermes CEO Console 앱을 엽니다.
4. 첫 화면에서 `Setup Wizard` 또는 `처음 설치` 버튼을 누릅니다.
5. 별도 CMD/PowerShell 창이 열리면 닫지 말고 완료될 때까지 기다립니다.
6. 설치가 끝나면 앱으로 돌아가 `Retry / Check Again` 또는 `다시 확인`을 누릅니다.
7. 정상 설치되면 `http://127.0.0.1:8788` WebUI가 열립니다.
8. WebUI의 Paperclip 탭에서 `http://127.0.0.1:3100` Paperclip 화면이 표시됩니다.

### 4.2 WSL/Ubuntu가 없는 경우

Installer가 WSL 또는 Ubuntu가 없다고 안내하면 관리자 PowerShell에서 아래 명령을 실행합니다.

```powershell
wsl --install -d Ubuntu
```

Microsoft Store 또는 기본 설치가 막히는 환경에서는 다음 fallback을 시도합니다.

```powershell
wsl --install --web-download -d Ubuntu
```

Windows가 재시작을 요구하면 재시작합니다. 그 다음 Ubuntu 앱을 한 번 직접 열어 Linux username/password를 생성합니다. 비밀번호 입력 중 화면에 아무 글자도 보이지 않는 것은 정상입니다.

Ubuntu 초기화가 끝난 뒤 Hermes CEO Console을 다시 열고 `Setup Wizard`를 다시 누르면 Hermes Agent / FMG WebUI / FMG Paperclip 설치 단계로 이어집니다.

### 4.3 PowerShell script pack 설치

EXE 대신 script pack으로 설치하려면 PowerShell에서 실행합니다.

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
Invoke-WebRequest -Uri "https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/hermes-ceo-console-installer-pack.zip" -OutFile "hermes-ceo-console-installer-pack.zip"
Expand-Archive .\hermes-ceo-console-installer-pack.zip -DestinationPath .\hermes-ceo-console-installer -Force
cd .\hermes-ceo-console-installer
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1 -Yes -SkipCodex -SkipTelegram -SkipOpenCrab
```

`-SkipPaperclip`은 기본 사용하지 마세요. 이 installer의 현재 릴리스부터는 FMG 커스터마이징 Paperclip이 기본 설치 대상입니다.

### 4.4 Windows 설치 중 보이는 단계

설치 창에는 대략 다음 단계가 표시됩니다.

1. WSL2 사용 가능 여부 확인
2. Ubuntu distro 설치/초기화 여부 확인
3. Ubuntu 안에 `python3`, `git`, `curl` 설치
4. Hermes Agent 설치/업데이트
5. FMG Hermes WebUI clone/update 및 commit 검증
6. FMG Paperclip clone/update 및 commit 검증
7. Node 20 / pnpm 9.15.4 준비
8. Paperclip dependency install
9. Paperclip 실행 및 `/api/health` 확인
10. Hermes WebUI 실행 및 `/health` 확인
11. Windows 브라우저에서 WebUI 열기

첫 설치는 몇 분 걸릴 수 있습니다. 특히 Node/pnpm/Paperclip dependency 설치 구간은 오래 걸릴 수 있으므로 창을 닫지 마세요.

---

## 5. macOS 설치 방법

macOS는 WSL 없이 로컬에서 Hermes Agent / WebUI / Paperclip을 실행합니다.

### 5.1 DMG 설치

1. Release에서 DMG를 다운로드합니다.

```text
https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/hermes-ceo-console-macos-arm64.dmg
```

2. DMG를 열고 앱을 Applications로 이동합니다.
3. 앱을 실행합니다.
4. Setup 화면이 나오면 `Run Setup Wizard`를 누릅니다.

Unsigned 또는 notarization 상태에 따라 Gatekeeper 경고가 보일 수 있습니다. 이 경우 시스템 설정의 보안 허용 또는 우클릭 > 열기 흐름이 필요할 수 있습니다.

### 5.2 script pack 설치

```bash
curl -L -o hermes-ceo-console-installer-pack.zip https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/hermes-ceo-console-installer-pack.zip
unzip hermes-ceo-console-installer-pack.zip -d hermes-ceo-console-installer
cd hermes-ceo-console-installer
chmod +x install-macos.sh scripts/first_run_wizard.py
./install-macos.sh
```

비밀값 입력 없이 기본 설치만 먼저 하려면:

```bash
./install-macos.sh --yes --skip-telegram --skip-opencrab --skip-codex
```

macOS에서도 Paperclip을 기본 설치/실행하려면 `--skip-paperclip`을 넣지 마세요.

---

## 6. 설치 후 필수 확인 명령

### 6.1 Windows 확인

PowerShell에서 실행합니다.

```powershell
wsl bash -lc "hermes --version"
wsl bash -lc "cd ~/.hermes/hermes-agent && git remote get-url origin && git rev-parse HEAD"
wsl bash -lc "cd ~/.hermes/webui/workspace/hermes-for-web && git remote get-url origin && git rev-parse HEAD"
wsl bash -lc "cd ~/.hermes/webui/workspace/paperclip && git remote get-url origin && git rev-parse HEAD"
wsl bash -lc "curl -fsS http://127.0.0.1:3100/api/health && echo && curl -fsS http://127.0.0.1:8788/health"
```

기대값:

```text
Hermes WebUI origin: https://github.com/contentscoin/hermes-for-web.git
Hermes WebUI HEAD:   d6cf50a59b34b3a5534d96cf9732a6a2523413dd

Paperclip origin:    https://github.com/contentscoin/paperclip.git
Paperclip HEAD:      72bb0505a09d5b789a8a88c6cbd26c024b2e4215
```

### 6.2 macOS 확인

```bash
hermes --version
cd ~/.hermes/hermes-agent && git remote get-url origin && git rev-parse HEAD
cd ~/.hermes/webui/workspace/hermes-for-web && git remote get-url origin && git rev-parse HEAD
cd ~/.hermes/webui/workspace/paperclip && git remote get-url origin && git rev-parse HEAD
curl -fsS http://127.0.0.1:3100/api/health
curl -fsS http://127.0.0.1:8788/health
```

### 6.3 WebUI 화면 확인

브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:8788
```

확인할 것:

- Hermes CEO Console UI가 열린다.
- 왼쪽/상단의 Paperclip 탭을 누르면 Paperclip 화면이 iframe으로 보인다.
- Paperclip 직접 주소 `http://127.0.0.1:3100`도 열린다.
- Paperclip issue/detail 화면이 blank가 아니고 실제 내용이 보인다.

---

## 7. 세부 설정 방법

### 7.1 Hermes Agent 기본 설정

설치 후 모델/provider 설정을 하려면 터미널에서 실행합니다.

Windows:

```powershell
wsl bash -lc "hermes setup"
wsl bash -lc "hermes doctor"
```

macOS:

```bash
hermes setup
hermes doctor
```

자주 쓰는 명령:

```bash
hermes model
hermes config
hermes config edit
hermes status --all
hermes tools list
hermes skills list
```

설정 파일:

```text
~/.hermes/config.yaml
```

비밀값 파일:

```text
~/.hermes/.env
```

### 7.2 모델/provider 설정

대화 모델은 `hermes model`에서 선택하는 것이 가장 안전합니다.

```bash
hermes model
```

직접 설정할 수도 있습니다.

```bash
hermes config set model.provider openrouter
hermes config set model.default openai/gpt-5.5
```

Provider API key는 보통 `~/.hermes/.env`에 저장합니다. 예시는 아래와 같지만 실제 key는 README나 GitHub에 절대 넣지 마세요.

```text
OPENROUTER_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
```

설정 변경 후에는 새 Hermes 세션 또는 gateway 재시작이 필요할 수 있습니다.

### 7.3 Codex CLI 설정

Codex login은 자동으로 끝낼 수 없습니다. OAuth/device flow는 사용자가 직접 승인해야 합니다.

macOS:

```bash
codex --version
codex login
```

Windows WSL:

```powershell
wsl bash -lc "codex --version && codex login"
```

설치 wizard의 quick setup은 Codex login을 기본으로 건너뜁니다. WebUI가 먼저 열린 뒤 필요할 때 설정하세요.

### 7.4 Telegram bot 설정

Telegram bot token은 BotFather에서 생성합니다.

1. https://t.me/BotFather 열기
2. `/newbot` 실행
3. bot 이름과 username 지정
4. token 복사
5. `~/.hermes/.env` 또는 `hermes gateway setup`에서 설정

일반 명령:

```bash
hermes gateway setup
hermes gateway run
```

서비스로 실행하려면:

```bash
hermes gateway install
hermes gateway start
hermes gateway status
```

Windows WSL에서는 앞에 `wsl bash -lc`를 붙여 실행합니다.

```powershell
wsl bash -lc "hermes gateway setup"
wsl bash -lc "hermes gateway run"
```

주의:

- Telegram token은 화면에 다시 출력하지 않습니다.
- token은 repo에 저장하지 않습니다.
- 실제 Telegram 메시지 전송은 항상 대상과 문구 확인 후 진행해야 합니다.
- Paperclip 반영은 Telegram 대화만으로 자동 실행하지 않습니다.

### 7.5 Paperclip 설정

alpha.9부터 installer는 FMG 커스터마이징 Paperclip을 기본 설치합니다.

기본값:

```text
PAPERCLIP_WEB_URL=http://127.0.0.1:3100
PAPERCLIP_BASE_URL=http://127.0.0.1:3100
PAPERCLIP_DEFAULT_COMPANY=FMG
```

설정 위치:

```text
~/.hermes/.env
```

직접 확인:

```bash
grep -E '^PAPERCLIP_' ~/.hermes/.env
```

Windows:

```powershell
wsl bash -lc "grep -E '^PAPERCLIP_' ~/.hermes/.env"
```

Paperclip 실행 상태 확인:

```bash
curl -fsS http://127.0.0.1:3100/api/health
```

Windows:

```powershell
wsl bash -lc "curl -fsS http://127.0.0.1:3100/api/health"
```

Paperclip 수동 실행:

```bash
cd ~/.hermes/webui/workspace/paperclip
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20
pnpm paperclipai run --instance default
```

Windows:

```powershell
wsl bash -lc "cd ~/.hermes/webui/workspace/paperclip && export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && nvm use 20 && pnpm paperclipai run --instance default"
```

Paperclip 운영 원칙:

- WebUI의 Paperclip 탭은 실제 Paperclip 화면을 보여주는 용도입니다.
- Paperclip issue/comment/status update는 자동 실행하지 않습니다.
- Telegram/Hermes 논의는 Paperclip에 자동 반영하지 않습니다.
- 항상 Decision Report 또는 결과 보고서를 먼저 만들고, 사용자의 명시 승인 후에만 반영합니다.

승인 예시:

```text
승인
반영해
Paperclip 반영 승인
comment만 반영해
issue create 승인
full execution 승인
```

승인으로 보지 않는 예시:

```text
좋아
오케이
괜찮네
그 방향으로 보자
맞는 듯
```

### 7.6 Paperclip Workflow Control Pack

installer에는 Paperclip live workflow 상태를 read-only로 점검하고, 필요한 경우 명시 승인 후 routine을 조정할 수 있는 로컬 스크립트가 포함됩니다.

기본 진단:

```bash
python3 scripts/paperclip_workflow_control.py status
python3 scripts/paperclip_workflow_control.py --format json status --company FMG
```

Windows:

```powershell
wsl bash -lc "cd ~/.hermes/webui/workspace/hermes-ceo-console-installer && python3 scripts/paperclip_workflow_control.py status"
```

Issue Workflow DAG 확인:

```bash
python3 scripts/paperclip_workflow_control.py issue-workflow WORK-2371
python3 scripts/paperclip_workflow_control.py --format json issue-workflow WORK-2371
```

진단 항목:

- Paperclip `/api/health`
- company/project/routine/live-run 수
- routine status 요약
- scheduler heartbeat 요약
- duplicate/similar routine title 감지
- installed plugin/tool 목록
- issue별 Live Workflow DAG API 가용성
- node/edge 수
- raw event message/payload sanitize 여부

조정 기능은 dry-run이 기본입니다.

```bash
python3 scripts/paperclip_workflow_control.py pause-routine ROUTINE_ID
python3 scripts/paperclip_workflow_control.py resume-routine ROUTINE_ID
python3 scripts/paperclip_workflow_control.py run-routine ROUTINE_ID
python3 scripts/paperclip_workflow_control.py update-trigger TRIGGER_ID --cron "0 9 * * *" --timezone Asia/Seoul
```

실제 반영은 반드시 `--apply --confirm APPLY`를 같이 넣어야 합니다.

```bash
python3 scripts/paperclip_workflow_control.py resume-routine ROUTINE_ID --apply --confirm APPLY
```

### 7.7 OpenCrab MCP 설정

OpenCrab은 Hermes/Paperclip 의사결정에 ontology evidence를 붙이기 위한 선택 통합입니다. endpoint URL에 key가 포함될 수 있으므로 README, issue comment, log, 보고서에는 원문을 남기지 마세요.

예시 형태:

```yaml
mcp_servers:
  opencrab:
    url: "https://opencrab.sh/api/mcp/[REDACTED]"
    timeout: 180
    connect_timeout: 60
```

설정 후 확인:

```bash
hermes mcp list
hermes mcp test opencrab
```

Windows:

```powershell
wsl bash -lc "hermes mcp list && hermes mcp test opencrab"
```

원칙:

- endpoint/key는 repo, README, Paperclip comment에 저장하지 않습니다.
- Hermes gateway/agent 재시작 후 MCP tool discovery가 적용됩니다.
- OpenCrab ingest/mutation은 기본 비활성으로 유지합니다.
- 별도 승인 없이는 자동 ingest를 실행하지 않습니다.

---

## 8. 실행/재실행 방법

### 8.1 Windows 앱 실행

일반적으로 Start Menu 또는 Desktop shortcut에서 Hermes CEO Console을 실행합니다.

수동으로 WebUI와 Paperclip을 재시작해야 할 때:

```powershell
wsl bash -lc "mkdir -p ~/.hermes/logs; export NVM_DIR=\"$HOME/.nvm\"; [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && nvm use 20 >/dev/null; cd ~/.hermes/webui/workspace/paperclip && nohup pnpm paperclipai run --instance default >> ~/.hermes/logs/paperclip-fmg.log 2>&1 & cd ~/.hermes/webui/workspace/hermes-for-web && ./start.sh 8788 >> ~/.hermes/logs/hermes-ceo-console.log 2>&1"
```

### 8.2 macOS 앱 실행

앱 또는 launcher를 실행하면 WebUI health를 확인하고, 필요하면 `~/.hermes/webui/workspace/hermes-for-web/start.sh`를 실행합니다.

수동 실행:

```bash
mkdir -p ~/.hermes/logs
cd ~/.hermes/webui/workspace/paperclip
nohup pnpm paperclipai run --instance default >> ~/.hermes/logs/paperclip-fmg.log 2>&1 &
cd ~/.hermes/webui/workspace/hermes-for-web
./start.sh 8788
```

---

## 9. 로그와 상태 확인

### 9.1 WebUI 로그

macOS:

```bash
tail -100 ~/.hermes/logs/hermes-ceo-console.log
```

Windows:

```powershell
wsl bash -lc "tail -100 ~/.hermes/logs/hermes-ceo-console.log"
```

### 9.2 Paperclip 로그

macOS:

```bash
tail -100 ~/.hermes/logs/paperclip-fmg.log
```

Windows:

```powershell
wsl bash -lc "tail -100 ~/.hermes/logs/paperclip-fmg.log"
```

### 9.3 포트 확인

macOS:

```bash
lsof -nP -iTCP:8788 -sTCP:LISTEN
lsof -nP -iTCP:3100 -sTCP:LISTEN
```

Windows PowerShell:

```powershell
netstat -ano | findstr :8788
netstat -ano | findstr :3100
```

WSL 내부:

```powershell
wsl bash -lc "ss -ltnp | grep -E ':8788|:3100' || true"
```

---

## 10. 업데이트 방법

### 10.1 installer 자체 업데이트

새 release EXE 또는 script pack을 받아 다시 실행합니다. 기존 WSL/Ubuntu와 `~/.hermes` 데이터는 유지됩니다.

### 10.2 Hermes WebUI / Paperclip 업데이트

Setup Wizard를 다시 실행하면 installer가 다음을 수행합니다.

- 기존 `hermes-for-web`의 origin이 FMG repo가 아니면 FMG repo로 변경
- `origin/main` fetch
- expected commit으로 reset/검증
- 기존 `paperclip`의 origin이 FMG repo가 아니면 FMG repo로 변경
- `live/opencrab-default-dag-20260510` fetch
- expected commit으로 reset/검증

주의: 이 흐름은 설치 디렉터리의 로컬 수정사항을 reset할 수 있습니다. 설치 디렉터리에서 직접 개발 중이었다면 먼저 별도 branch나 patch로 백업하세요.

---

## 11. 문제 해결

### 11.1 WebUI가 열리지 않음

확인:

```bash
curl -fsS http://127.0.0.1:8788/health
```

Windows:

```powershell
wsl bash -lc "curl -fsS http://127.0.0.1:8788/health"
wsl bash -lc "tail -100 ~/.hermes/logs/hermes-ceo-console.log"
```

가능 원인:

- WSL/Ubuntu가 아직 초기화되지 않음
- WebUI process가 실행되지 않음
- 8788 포트 충돌
- 오래된 WebUI process가 다른 clone에서 실행 중

### 11.2 Paperclip 탭이 비어 있음

먼저 Paperclip 자체 health를 확인합니다.

```bash
curl -fsS http://127.0.0.1:3100/api/health
```

Windows:

```powershell
wsl bash -lc "curl -fsS http://127.0.0.1:3100/api/health"
wsl bash -lc "tail -100 ~/.hermes/logs/paperclip-fmg.log"
```

가능 원인:

- Paperclip server가 실행되지 않음
- 3100 포트 충돌
- dependency install 실패
- WebUI가 오래된 process라 Paperclip iframe/status route가 반영되지 않음
- 브라우저 onboarding/modal이 iframe을 가리고 있음

해결 순서:

1. `http://127.0.0.1:3100` 직접 열기
2. `http://127.0.0.1:3100/api/health` 확인
3. WebUI 새로고침
4. WebUI/Paperclip process 재시작
5. 로그 확인

### 11.3 Hermes Agent / WebUI / Paperclip 버전 확인

현재 installer 기준 Hermes Agent는 `v0.14.0 (2026.5.16)` / commit `973f27e95631aaecbda5e32e3fa9e5d7f6a2e1d3`입니다. FMG WebUI/Paperclip 설치 확인은 아래처럼 source commit까지 함께 봐야 합니다.

```bash
hermes --version
cd ~/.hermes/hermes-agent && git remote get-url origin && git rev-parse HEAD
cd ~/.hermes/webui/workspace/hermes-for-web && git remote get-url origin && git rev-parse HEAD
cd ~/.hermes/webui/workspace/paperclip && git remote get-url origin && git rev-parse HEAD
```

Windows:

```powershell
wsl bash -lc "hermes --version"
wsl bash -lc "cd ~/.hermes/hermes-agent && git remote get-url origin && git rev-parse HEAD"
wsl bash -lc "cd ~/.hermes/webui/workspace/hermes-for-web && git remote get-url origin && git rev-parse HEAD"
wsl bash -lc "cd ~/.hermes/webui/workspace/paperclip && git remote get-url origin && git rev-parse HEAD"
```

### 11.4 Windows에서 WSL 연결 실패

```powershell
wsl -l -v
wsl -d Ubuntu -- bash -lc "printf wsl-ready"
```

Ubuntu가 목록에 없으면:

```powershell
wsl --install -d Ubuntu
```

Ubuntu는 있는데 ready check가 실패하면 Ubuntu 앱을 직접 열어 username/password 초기화를 완료하세요.

### 11.5 Node/pnpm 문제

Paperclip은 Node 20 계열과 pnpm 9.15.4 기준으로 맞춥니다.

확인:

```bash
node --version
pnpm --version
```

Windows:

```powershell
wsl bash -lc "export NVM_DIR=\"$HOME/.nvm\"; [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\"; node --version; pnpm --version"
```

수동 복구:

```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm install 20
nvm use 20
corepack enable
corepack prepare pnpm@9.15.4 --activate
```

### 11.6 SmartScreen / Gatekeeper 경고

현재 alpha installer는 code signing/notarization이 제한적일 수 있습니다.

- Windows SmartScreen: `추가 정보` > `실행`
- macOS Gatekeeper: 우클릭 > 열기 또는 시스템 설정 > 개인정보 보호 및 보안에서 허용

장기 과제:

- Apple Developer ID signing/notarization
- Windows Authenticode signing
- auto-update

---

## 12. 보안 및 운영 원칙

1. 이 repo에는 secret이 없습니다.
2. `.env`, token, OAuth cache, API key는 commit하지 않습니다.
3. setup wizard는 secret 값을 다시 출력하지 않습니다.
4. OpenCrab endpoint는 key를 포함할 수 있으므로 항상 `https://opencrab.sh/api/mcp/[REDACTED]` 형태로만 문서화합니다.
5. Telegram 전송은 대상과 문구 확인 후에만 실행합니다.
6. Paperclip 반영은 Decision Report / 결과 보고 후 명시 승인 시에만 실행합니다.
7. read-only 진단은 승인 없이 가능하지만, pause/resume/manual-run/update 같은 변경 작업은 dry-run preview와 명시 승인이 필요합니다.
8. Installer는 로컬 개발용 alpha입니다. 조직 배포 전 signing, notarization, checksum 검증을 권장합니다.

---

## 13. 포함 파일

```text
README.md
NOTICE.md
LICENSE
installer.manifest.json
install-macos.sh
install-windows.ps1
scripts/
  first_run_wizard.py
  install-wsl-runtime.ps1
  wsl-hermes-start.ps1
  paperclip_workflow_control.py
templates/
  .env.example
profiles/
  fmg.profile.json
electron-wrapper/
  main.js
  preload.js
  setup.html
  setup.js
  package.json
.github/workflows/
  release.yml
```

---

## 14. 개발자 빌드

### 14.1 Script installer zip

```bash
zip -r hermes-ceo-console-installer-pack.zip install-macos.sh install-windows.ps1 scripts templates profiles installer.manifest.json README.md NOTICE.md LICENSE docs/SIGNING.md
shasum -a 256 hermes-ceo-console-installer-pack.zip > hermes-ceo-console-installer-pack.zip.sha256
```

### 14.2 macOS DMG

```bash
cd electron-wrapper
npm install
npm run build:mac
```

결과:

```text
electron-wrapper/dist/*.dmg
```

### 14.3 Windows EXE

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

### 14.4 릴리스 검증 체크리스트

```bash
python3 -m json.tool installer.manifest.json
python3 -m json.tool profiles/fmg.profile.json
python3 -m py_compile scripts/first_run_wizard.py scripts/paperclip_workflow_control.py
bash -n install-macos.sh
node --check electron-wrapper/main.js
node --check electron-wrapper/setup.js
node --check electron-wrapper/preload.js
```

Release asset 확인:

```bash
curl -L -I https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/Hermes.CEO.Console.Setup.0.1.0-alpha.17.exe
curl -L -I https://github.com/contentscoin/hermes-ceo-console-installer/releases/download/v0.1.0-alpha.17/hermes-ceo-console-installer-pack.zip
```

Script pack 내용 확인:

```bash
python3 - <<'PY'
import zipfile
z=zipfile.ZipFile('hermes-ceo-console-installer-pack.zip')
for name in ['scripts/first_run_wizard.py','scripts/wsl-hermes-start.ps1','installer.manifest.json','README.md']:
    print(name, name in z.namelist())
PY
```

---

## 15. 현재 상태와 다음 과제

현재 상태:

- alpha installer pack
- Windows WSL2-first installer
- macOS script/DMG installer
- FMG Hermes WebUI 기본 설치
- FMG Paperclip 기본 설치
- Paperclip live iframe 연동
- Paperclip Workflow Control read-only 진단
- OpenCrab 선택 설정
- Telegram/Codex 후속 설정 가이드
- secret-free profile/manifest
- README/NOTICE 출처 및 오픈소스 고지

남은 과제:

- Apple Developer ID signing/notarization
- Windows Authenticode signing
- auto-update
- richer in-app setup status
- Windows 실제 설치 환경별 QA matrix 확대
- Paperclip workflow diagnostics UI 통합 강화
