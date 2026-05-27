const { app, BrowserWindow, shell, ipcMain, dialog, Menu } = require('electron');
const { spawn, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const https = require('https');

const port = process.env.HERMES_WEBUI_PORT || '8788';
const wslDistro = process.env.HERMES_WSL_DISTRO || 'Ubuntu';
const webUrl = `http://127.0.0.1:${port}`;
let win = null;
let child = null;
let paperclipChild = null;
const paperclipPort = process.env.PAPERCLIP_PORT || '3100';
const defaultPaperclipUrl = 'http://127.0.0.1:3100';
const defaultPaperclipHealthUrl = 'http://127.0.0.1:3100/api/health';
const paperclipUrl = process.env.PAPERCLIP_WEB_URL || (paperclipPort === '3100' ? defaultPaperclipUrl : `http://127.0.0.1:${paperclipPort}`);
const paperclipHealthUrl = paperclipUrl === defaultPaperclipUrl ? defaultPaperclipHealthUrl : `${paperclipUrl.replace(/\/$/, '')}/api/health`;

const updateOwner = 'contentscoin';
const updateRepo = 'hermes-ceo-console-installer';
const updateApiUrl = `https://api.github.com/repos/${updateOwner}/${updateRepo}/releases/latest`;
const updatePageUrl = `https://github.com/${updateOwner}/${updateRepo}/releases/latest`;
const updateCheckIntervalMs = Number(process.env.HERMES_UPDATE_CHECK_MS || 6 * 60 * 60 * 1000);
let lastUpdatePromptTag = null;
let autoSetupStarted = false;

function currentVersion(){
  try { return require('./package.json').version || '0.0.0'; }
  catch (_) { return '0.0.0'; }
}
function normalizeVersionTag(value){ return String(value || '').trim().replace(/^v/i, ''); }
function versionParts(value){
  const normalized = normalizeVersionTag(value);
  const match = normalized.match(/^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z]+)\.(\d+))?/);
  if(!match) return [0,0,0,'',0];
  return [Number(match[1]), Number(match[2]), Number(match[3]), match[4] || '', Number(match[5] || 0)];
}
function compareVersions(a,b){
  const pa = versionParts(a);
  const pb = versionParts(b);
  for(let i=0;i<3;i++){ if(pa[i] !== pb[i]) return pa[i] > pb[i] ? 1 : -1; }
  if(pa[3] !== pb[3]){
    if(!pa[3]) return 1;
    if(!pb[3]) return -1;
    return pa[3] > pb[3] ? 1 : -1;
  }
  if(pa[4] !== pb[4]) return pa[4] > pb[4] ? 1 : -1;
  return 0;
}
function selectUpdateAsset(release){
  const assets = Array.isArray(release && release.assets) ? release.assets : [];
  const platform = process.platform;
  const candidates = platform === 'win32'
    ? [/Hermes\.CEO\.Console\.Setup\..*\.exe$/i, /\.exe$/i]
    : platform === 'darwin'
      ? [/hermes-ceo-console-macos.*\.dmg$/i, /\.dmg$/i]
      : [/hermes-ceo-console-installer-pack\.zip$/i, /\.zip$/i];
  for(const pattern of candidates){
    const asset = assets.find(a => pattern.test(String(a.name || '')) && a.browser_download_url);
    if(asset) return asset;
  }
  return null;
}
function fetchLatestRelease(){
  return new Promise((resolve, reject) => {
    const req = https.get(updateApiUrl, {headers:{'User-Agent':'Hermes-CEO-Console-Updater','Accept':'application/vnd.github+json'}}, res => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', chunk => { body += chunk; });
      res.on('end', () => {
        if(res.statusCode < 200 || res.statusCode >= 300) return reject(new Error(`GitHub latest release returned HTTP ${res.statusCode}`));
        try { resolve(JSON.parse(body)); }
        catch(err){ reject(err); }
      });
    });
    req.setTimeout(8000, () => req.destroy(new Error('update_check_timeout')));
    req.on('error', reject);
  });
}
async function checkForUpdates({interactive=false}={}){
  try {
    const release = await fetchLatestRelease();
    const latestTag = String(release.tag_name || '');
    const latestVersion = normalizeVersionTag(latestTag);
    const localVersion = currentVersion();
    const asset = selectUpdateAsset(release);
    const updateAvailable = compareVersions(latestVersion, localVersion) > 0;
    const result = {ok:true, updateAvailable, localVersion, latestVersion, latestTag, releaseUrl:release.html_url || updatePageUrl, assetName:asset && asset.name, assetUrl:asset && asset.browser_download_url};
    appendLog(`update check ok local=${localVersion} latest=${latestVersion} available=${updateAvailable} asset=${result.assetName || 'none'}`);
    if(updateAvailable && win && (interactive || lastUpdatePromptTag !== latestTag)){
      lastUpdatePromptTag = latestTag;
      const response = await dialog.showMessageBox(win, {
        type:'info',
        buttons: asset ? ['업데이트 다운로드', '릴리즈 페이지', '나중에'] : ['릴리즈 페이지', '나중에'],
        defaultId:0,
        cancelId: asset ? 2 : 1,
        title:'Hermes CEO Console 업데이트 가능',
        message:`새 버전 ${latestTag} 이 GitHub에 배포되었습니다.`,
        detail:`현재 버전: ${localVersion}\n최신 버전: ${latestVersion}\n${asset ? `다운로드: ${asset.name}` : '이 플랫폼에 맞는 설치 파일을 릴리즈 페이지에서 확인하세요.'}`
      });
      if(asset && response.response === 0) await shell.openExternal(asset.browser_download_url);
      else if((asset && response.response === 1) || (!asset && response.response === 0)) await shell.openExternal(release.html_url || updatePageUrl);
    } else if(interactive && win){
      await dialog.showMessageBox(win, {
        type:'info',
        buttons:['확인'],
        title:'Hermes CEO Console 업데이트 확인',
        message:updateAvailable ? `새 버전 ${latestTag} 이 있습니다.` : '현재 최신 버전입니다.',
        detail:`현재 버전: ${localVersion}\n최신 버전: ${latestVersion || '(unknown)'}`
      });
    }
    return result;
  } catch(err){
    appendLog(`update check failed: ${err && err.message ? err.message : err}`);
    const result = {ok:false, error:err && err.message ? err.message : String(err), localVersion:currentVersion(), releaseUrl:updatePageUrl};
    if(interactive && win){
      await dialog.showMessageBox(win, {type:'warning', buttons:['릴리즈 페이지 열기','닫기'], title:'업데이트 확인 실패', message:'GitHub 최신 버전을 확인하지 못했습니다.', detail:`${result.error}\n\n수동 확인: ${updatePageUrl}`}).then(async r => { if(r.response === 0) await shell.openExternal(updatePageUrl); });
    }
    return result;
  }
}
function scheduleUpdateChecks(){
  setTimeout(() => checkForUpdates({interactive:false}), 10000);
  if(updateCheckIntervalMs > 0) setInterval(() => checkForUpdates({interactive:false}), updateCheckIntervalMs);
}

function appendLog(message){
  try {
    const p = logPath();
    fs.mkdirSync(path.dirname(p), {recursive:true});
    fs.appendFileSync(p, `[${new Date().toISOString()}] ${message}\n`);
  } catch (_) {}
}

function homeDir(){ return app.getPath('home'); }
function webuiDir(){ return process.env.HERMES_WEBUI_DIR || path.join(homeDir(), '.hermes', 'webui', 'workspace', 'hermes-for-web'); }
function logPath(){ return path.join(homeDir(), '.hermes', 'logs', 'hermes-ceo-console.log'); }
function paperclipLogPath(){ return path.join(homeDir(), '.hermes', 'logs', 'paperclip-fmg.log'); }
function ensureLogFd(){
  const p = logPath();
  fs.mkdirSync(path.dirname(p), {recursive:true});
  return fs.openSync(p, 'a');
}
function installerRoot(){
  if (process.resourcesPath && fs.existsSync(path.join(process.resourcesPath, 'installer'))) return path.join(process.resourcesPath, 'installer');
  return path.join(__dirname, '..');
}
function windowsWslRuntimeExists(){
  if(process.platform !== 'win32') return false;
  try {
    const command = 'test -f ~/.hermes/webui/workspace/hermes-for-web/start.sh -o -f ~/.hermes/webui/workspace/hermes-for-web/server.py && printf yes || printf no';
    const out = execFileSync('wsl.exe', ['-d', wslDistro, '--', 'bash', '-lc', command], {encoding:'utf8', timeout:5000, windowsHide:true});
    return String(out).trim() === 'yes';
  } catch (err) {
    appendLog(`windowsWslRuntimeExists failed: ${err && err.message ? err.message : err}`);
    return false;
  }
}
function runtimeExists(){
  const dir = webuiDir();
  if(fs.existsSync(path.join(dir, 'start.sh')) || fs.existsSync(path.join(dir, 'server.py'))) return true;
  return windowsWslRuntimeExists();
}
function probeHttpOk(url){
  return new Promise(resolve => {
    const req = http.get(url, res => { res.resume(); resolve(res.statusCode >= 200 && res.statusCode < 300); });
    req.setTimeout(1500, () => { req.destroy(); resolve(false); });
    req.on('error', () => resolve(false));
  });
}
function health(){ return probeHttpOk(`${webUrl}/health`); }
function paperclipHealth(){ return probeHttpOk(paperclipHealthUrl); }
async function waitForHealth(seconds=35){
  const deadline = Date.now() + seconds * 1000;
  while(Date.now() < deadline){
    if(await health()) return true;
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  return false;
}
async function waitForPaperclipHealth(seconds=35){
  const deadline = Date.now() + seconds * 1000;
  while(Date.now() < deadline){
    if(await paperclipHealth()) return true;
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  return false;
}
function killPaperclipChild(){
  if(!paperclipChild || paperclipChild.killed) return;
  try {
    appendLog(`stopping tracked paperclip child pid=${paperclipChild.pid || 'unknown'}`);
    if(process.platform === 'win32') paperclipChild.kill();
    else process.kill(-paperclipChild.pid, 'SIGTERM');
  } catch(err){
    try { paperclipChild.kill('SIGTERM'); } catch (_) {}
    appendLog(`paperclip child stop warning: ${err && err.message ? err.message : err}`);
  }
  paperclipChild = null;
}
async function startPaperclipServer({showDialog=false}={}){
  appendLog(`startPaperclipServer requested url=${paperclipUrl} platform=${process.platform}`);
  if(await paperclipHealth()){
    appendLog('startPaperclipServer skipped: already healthy');
    if(showDialog && win){
      await dialog.showMessageBox(win, {type:'info', buttons:['확인'], title:'Paperclip 서버', message:'Paperclip 서버가 이미 실행 중입니다.', detail:`Paperclip: ${paperclipUrl}\nLog: ${paperclipLogPath()}`});
    }
    return {started:false, healthy:true, alreadyRunning:true, paperclipUrl, logPath:paperclipLogPath()};
  }
  fs.mkdirSync(path.dirname(paperclipLogPath()), {recursive:true});
  const logFd = fs.openSync(paperclipLogPath(), 'a');
  try {
    if(process.platform === 'win32'){
      const command = `mkdir -p ~/.hermes/logs; export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 >/dev/null 2>&1 || true; if [ -d ~/.hermes/webui/workspace/paperclip ]; then cd ~/.hermes/webui/workspace/paperclip && (pnpm paperclipai run --instance default || npx -y paperclipai run --instance default); else cd ~/.hermes/webui/workspace && npx -y paperclipai run --instance default; fi`;
      paperclipChild = spawn('wsl.exe', ['-d', wslDistro, '--', 'bash', '-lc', command], {stdio:['ignore', logFd, logFd], detached:true});
    } else {
      const workspaceDir = path.join(homeDir(), '.hermes', 'webui', 'workspace');
      const localPaperclipDir = path.join(workspaceDir, 'paperclip');
      const command = fs.existsSync(localPaperclipDir)
        ? `export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 >/dev/null 2>&1 || true; cd ${quoteForShell(localPaperclipDir)}; pnpm paperclipai run --instance default || npx -y paperclipai run --instance default`
        : `export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 >/dev/null 2>&1 || true; cd ${quoteForShell(workspaceDir)}; npx -y paperclipai run --instance default`;
      paperclipChild = spawn('/bin/bash', ['-lc', command], {stdio:['ignore', logFd, logFd], detached:true});
    }
    paperclipChild.unref();
  } catch(err){
    appendLog(`startPaperclipServer spawn failed: ${err && err.message ? err.message : err}`);
    if(showDialog && win){
      await dialog.showMessageBox(win, {type:'error', buttons:['확인'], title:'Paperclip 서버 시작 실패', message:'Paperclip 서버 시작 명령을 실행하지 못했습니다.', detail:`${err && err.message ? err.message : err}\nLog: ${paperclipLogPath()}`});
    }
    return {started:false, healthy:false, error:err && err.message ? err.message : String(err), paperclipUrl, logPath:paperclipLogPath()};
  }
  const healthy = await waitForPaperclipHealth(45);
  appendLog(`startPaperclipServer result pid=${paperclipChild && paperclipChild.pid ? paperclipChild.pid : 'unknown'} healthy=${healthy}`);
  if(showDialog && win){
    await dialog.showMessageBox(win, {
      type: healthy ? 'info' : 'warning',
      buttons:['확인'],
      title:'Paperclip 서버 시작/복구',
      message: healthy ? 'Paperclip 서버가 시작되었습니다.' : 'Paperclip 시작 명령은 실행했지만 아직 응답하지 않습니다.',
      detail:`Paperclip: ${paperclipUrl}\nHealth: ${paperclipHealthUrl}\nLog: ${paperclipLogPath()}${healthy ? '' : '\n로그를 열어 오류를 확인하세요.'}`
    });
  }
  return {started:true, healthy, paperclipUrl, healthUrl:paperclipHealthUrl, logPath:paperclipLogPath()};
}

function killTrackedChild(){
  if(!child || child.killed) return;
  try {
    appendLog(`stopping tracked child pid=${child.pid || 'unknown'}`);
    if(process.platform === 'win32') child.kill();
    else process.kill(-child.pid, 'SIGTERM');
  } catch(err){
    try { child.kill('SIGTERM'); } catch (_) {}
    appendLog(`tracked child stop warning: ${err && err.message ? err.message : err}`);
  }
  child = null;
}
function stopListeningRuntime(){
  appendLog(`stopListeningRuntime requested port=${port} platform=${process.platform}`);
  killTrackedChild();
  try {
    if(process.platform === 'win32'){
      const command = `PORT=${port}; if command -v lsof >/dev/null 2>&1; then PIDS=$(lsof -tiTCP:$PORT -sTCP:LISTEN 2>/dev/null || true); [ -n "$PIDS" ] && kill $PIDS || true; fi; pkill -f "hermes-for-web.*(start.sh|server.py).*${port}" 2>/dev/null || true; pkill -f "server.py.*--port ${port}" 2>/dev/null || true; exit 0`;
      execFileSync('wsl.exe', ['-d', wslDistro, '--', 'bash', '-lc', command], {encoding:'utf8', timeout:8000, windowsHide:true});
    } else {
      const command = `PIDS=$(lsof -tiTCP:${port} -sTCP:LISTEN 2>/dev/null || true); if [ -n "$PIDS" ]; then kill $PIDS 2>/dev/null || true; sleep 1; for p in $PIDS; do kill -0 $p 2>/dev/null && kill -9 $p 2>/dev/null || true; done; fi`;
      execFileSync('/bin/bash', ['-lc', command], {encoding:'utf8', timeout:8000});
    }
  } catch(err){
    appendLog(`stopListeningRuntime warning: ${err && err.message ? err.message : err}`);
  }
}
async function restartRuntime({showDialog=false}={}){
  appendLog('restartRuntime requested');
  if(!runtimeExists()){
    appendLog('restartRuntime aborted: runtime missing');
    if(showDialog && win){
      await dialog.showMessageBox(win, {type:'warning', buttons:['Setup Wizard 열기','닫기'], title:'서버 재시작 불가', message:'Hermes WebUI 설치 경로를 찾지 못했습니다.', detail:'처음 설치 / Setup Wizard를 먼저 실행하세요.'}).then(async r => { if(r.response === 0) await runSetup(); });
    }
    return {started:false, healthy:false, error:'runtime_missing', logPath:logPath()};
  }
  stopListeningRuntime();
  await new Promise(resolve => setTimeout(resolve, 1200));
  const started = startExistingRuntime();
  const healthy = started ? await waitForHealth(45) : false;
  appendLog(`restartRuntime result started=${started} healthy=${healthy}`);
  if(healthy && win) await win.loadURL(webUrl);
  else if(win) loadSetup('existing-failed');
  if(showDialog && win){
    await dialog.showMessageBox(win, {
      type: healthy ? 'info' : 'warning',
      buttons:['확인'],
      title:'Hermes 서버 재시작/복구',
      message: healthy ? 'Hermes WebUI 서버가 재시작되어 복구되었습니다.' : '재시작 명령은 실행했지만 아직 WebUI가 응답하지 않습니다.',
      detail:`WebUI: ${webUrl}\nLog: ${logPath()}${healthy ? '' : '\n로그를 열어 오류를 확인하거나 Setup Wizard를 다시 실행하세요.'}`
    });
  }
  return {started, healthy, webUrl, logPath:logPath()};
}
function buildAppMenu(){
  const template = [
    ...(process.platform === 'darwin' ? [{role:'appMenu'}] : []),
    {
      label:'Hermes',
      submenu:[
        {label:'서버 재시작/복구', accelerator:'CmdOrCtrl+R', click:() => restartRuntime({showDialog:true})},
        {label:'Paperclip 서버 시작/복구', accelerator:'CmdOrCtrl+Shift+P', click:() => startPaperclipServer({showDialog:true})},
        {label:'상태 다시 확인', accelerator:'CmdOrCtrl+Shift+R', click:() => route()},
        {label:'WebUI 브라우저로 열기', click:() => shell.openExternal(webUrl)},
        {label:'Paperclip 브라우저로 열기', click:() => shell.openExternal(paperclipUrl)},
        {label:'로그 열기', click:async () => { const p=logPath(); if(fs.existsSync(p)) await shell.openPath(p); else dialog.showMessageBox({message:'Log file not found yet', detail:p}); }},
        {type:'separator'},
        {label:'업데이트 확인', click:() => checkForUpdates({interactive:true})},
        {type:'separator'},
        {role:'quit', label:'종료'}
      ]
    },
    {role:'editMenu', label:'편집'},
    {role:'viewMenu', label:'보기'},
    {role:'windowMenu', label:'창'}
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function loadSetup(mode){
  return win.loadFile(path.join(__dirname, 'setup.html'), {query: {mode, port, dir: webuiDir()}});
}
async function maybeAutoRunWindowsSetup(reason){
  if(process.platform !== 'win32') return null;
  if(process.env.HERMES_AUTO_SETUP_ON_START === '0') return null;
  if(autoSetupStarted) return null;
  autoSetupStarted = true;
  appendLog(`auto setup requested reason=${reason || 'unknown'} version=${currentVersion()}`);
  const result = await runSetup();
  appendLog(`auto setup result started=${result && result.started} mode=${result && result.mode ? result.mode : 'none'} error=${result && result.error ? result.error : 'none'}`);
  return result;
}
function startExistingRuntime(){
  if(!runtimeExists()) return false;
  const dir = webuiDir();
  const logFd = ensureLogFd();
  if(process.platform === 'win32'){
    const command = `mkdir -p ~/.hermes/logs; export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 >/dev/null; if [ -d ~/.hermes/webui/workspace/paperclip ]; then cd ~/.hermes/webui/workspace/paperclip && nohup pnpm paperclipai run --instance default >> ~/.hermes/logs/paperclip-fmg.log 2>&1 & fi; cd ~/.hermes/webui/workspace/hermes-for-web && ./start.sh ${port} >> ~/.hermes/logs/hermes-ceo-console.log 2>&1`;
    child = spawn('wsl.exe', ['-d', wslDistro, '--', 'bash', '-lc', command], {stdio:['ignore', logFd, logFd], detached:true});
  } else {
    const script = fs.existsSync(path.join(dir, 'start.sh')) ? './start.sh' : null;
    const args = script ? [script, port] : [process.env.PYTHON || 'python3', 'server.py', '--port', port];
    child = spawn(args[0], args.slice(1), {cwd:dir, stdio:['ignore', logFd, logFd], detached:true});
  }
  child.unref();
  return true;
}
function quoteForShell(s){ return `'${String(s).replace(/'/g, `'\\''`)}'`; }
function quoteForCmd(s){ return `"${String(s).replace(/"/g, '""')}"`; }
function writeWindowsSetupLauncher(script){
  const dir = path.join(app.getPath('userData'), 'setup-launcher');
  fs.mkdirSync(dir, {recursive:true});
  const launcher = path.join(dir, 'run-hermes-ceo-console-setup.cmd');
  const body = [
    '@echo off',
    'setlocal',
    'title Hermes CEO Console Setup',
    'echo Hermes CEO Console Setup',
    'echo.',
    'echo [What this window does]',
    'echo This command window automatically installs or updates Hermes Agent inside WSL,',
    'echo then updates the FMG-provided Hermes WebUI and Paperclip runtimes,',
    `echo then starts WebUI at http://127.0.0.1:${port} and Paperclip at http://127.0.0.1:3100.`,
    'echo It uses quick setup by default: Codex and Telegram prompts are skipped here;',
    'echo FMG-customized Paperclip is installed/started locally so the Paperclip tab works.',
    'echo Neo4j is optional: setup only checks/configures placeholders unless you enable it later.',
    'echo Do not close this window until the setup says it is complete.',
    'echo.',
    'echo [How to proceed]',
    'echo 1. If Windows asks for permission or shows SmartScreen, choose Run/Allow.',
    'echo 2. If WSL2 or Ubuntu is missing, this installer will try to install Ubuntu automatically.',
    'echo    If Windows asks for Administrator permission or a reboot, allow it and rerun setup.',
    'echo 3. If Ubuntu opens for the first time, create the Ubuntu username/password,',
    'echo    then return here and run Setup Wizard again. That second run continues to Hermes install.',
    'echo 4. When Ubuntu is ready, this setup automatically checks/updates Hermes Agent,',
    'echo    then checks/updates FMG WebUI and Paperclip.',
    'echo    This can take several minutes. Keep this window open until it prints Done.',
    'echo    Note: this installer targets Hermes Agent v0.14.0 and prints',
    'echo    Hermes source/WebUI/Paperclip commits for freshness checks.',
    'echo 5. The installer skips Codex/Telegram secret prompts by default.',
    'echo    It does install and start FMG-customized Paperclip locally.',
    'echo 6. When the setup finishes, go back to the Hermes CEO Console app and press',
    `echo    Retry / Check Again. The app should open http://127.0.0.1:${port}.`,
    'echo.',
    'echo [If nothing seems to happen]',
    'echo - Keep this window open and copy the last visible error line.',
    'echo - App log: %USERPROFILE%\\.hermes\\logs\\hermes-ceo-console.log',
    'echo - You can rerun this file by double-clicking it again.',
    'echo.',
    `powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File ${quoteForCmd(script)} -Port ${quoteForCmd(port)} -Distro ${quoteForCmd(wslDistro)} -Yes -SkipCodex -SkipTelegram -SkipNeo4j`,
    'set EXITCODE=%ERRORLEVEL%',
    'if not "%EXITCODE%"=="0" (',
    '  echo.',
    '  echo Setup command exited with code %EXITCODE%.',
    '  echo Keep this window open and copy the message if you need support.',
    '  pause',
    ')',
    'endlocal',
    '',
  ].join('\r\n');
  fs.writeFileSync(launcher, body, 'utf8');
  return launcher;
}
async function runSetup(){
  const root = installerRoot();
  const isWin = process.platform === 'win32';
  const script = isWin ? path.join(root, 'install-windows.ps1') : path.join(root, 'install-macos.sh');
  appendLog(`runSetup requested platform=${process.platform} script=${script}`);
  if(!fs.existsSync(script)){
    dialog.showErrorBox('Installer missing', script);
    appendLog(`runSetup installer missing script=${script}`);
    return {started:false, error:'installer_missing', script};
  }
  if(isWin){
    // Use a visible .cmd launcher and ask Windows Shell to open it. In packaged
    // Electron GUI apps, child_process spawn can silently fail or be hidden by
    // shell/security policy. Opening a command file gives the user a visible
    // console window and a concrete file to run manually if needed.
    const launcher = writeWindowsSetupLauncher(script);
    appendLog(`runSetup opening launcher=${launcher}`);
    const openError = await shell.openPath(launcher);
    if(openError){
      appendLog(`runSetup shell.openPath failed: ${openError}`);
      return {started:false, error:'open_launcher_failed', detail:openError, script, launcher};
    }
    return {started:true, mode:'windows-cmd-launcher', script, launcher};
  }
  if(process.platform === 'darwin'){
    const command = `/bin/bash ${quoteForShell(script)} --port ${quoteForShell(port)}`;
    const osa = `tell application "Terminal"\nactivate\ndo script ${JSON.stringify(command)}\nend tell`;
    child = spawn('/usr/bin/osascript', ['-e', osa], {detached:true, stdio:'ignore'});
    child.unref();
    return {started:true, mode:'mac-terminal', script};
  }
  const logFd = ensureLogFd();
  child = spawn('/bin/bash', [script, '--port', port], {stdio:['ignore', logFd, logFd], detached:true});
  child.unref();
  return {started:true, mode:'background-bash', script, logPath:logPath()};
}
async function route(){
  if(await health()){
    win.loadURL(webUrl);
    return;
  }
  if(runtimeExists()){
    await loadSetup('starting-existing');
    startExistingRuntime();
    if(await waitForHealth(35)) win.loadURL(webUrl);
    else {
      await loadSetup('existing-failed');
      await maybeAutoRunWindowsSetup('existing-runtime-unhealthy');
    }
    return;
  }
  await loadSetup('first-run');
  await maybeAutoRunWindowsSetup('runtime-missing');
}
function createWindow(){
  win = new BrowserWindow({width: 1280, height: 860, title: 'Hermes CEO Console', webPreferences:{preload:path.join(__dirname,'preload.js')}});
  win.webContents.setWindowOpenHandler(({url}) => { shell.openExternal(url); return {action:'deny'}; });
  route();
}
ipcMain.handle('health', health);
ipcMain.handle('runtime-status', async () => ({healthy: await health(), runtimeExists: runtimeExists(), webUrl, webuiDir: webuiDir(), logPath: logPath()}));
ipcMain.handle('open-webui', async () => { await shell.openExternal(webUrl); return true; });
ipcMain.handle('check-updates', async () => checkForUpdates({interactive:true}));
ipcMain.handle('retry', async () => { await route(); return true; });
ipcMain.handle('start-existing', async () => { const started = startExistingRuntime(); return {started, healthy: await waitForHealth(35)}; });
ipcMain.handle('restart-server', async () => restartRuntime({showDialog:false}));
ipcMain.handle('start-paperclip-server', async () => startPaperclipServer({showDialog:false}));
ipcMain.handle('paperclip-health', async () => ({healthy: await paperclipHealth(), paperclipUrl, healthUrl: paperclipHealthUrl, logPath: paperclipLogPath()}));
ipcMain.handle('run-setup', async () => runSetup());
ipcMain.handle('open-logs', async () => {
  const p = logPath();
  if(fs.existsSync(p)) await shell.openPath(p); else dialog.showMessageBox({message:'Log file not found yet', detail:p});
  return true;
});
app.whenReady().then(() => { buildAppMenu(); createWindow(); scheduleUpdateChecks(); });
app.on('window-all-closed', ()=>{ if(process.platform !== 'darwin') app.quit(); });
