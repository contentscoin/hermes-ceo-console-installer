const { app, BrowserWindow, shell, ipcMain, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');

const port = process.env.HERMES_WEBUI_PORT || '8788';
const wslDistro = process.env.HERMES_WSL_DISTRO || 'Ubuntu';
const webUrl = `http://127.0.0.1:${port}`;
let win = null;
let child = null;

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
function ensureLogFd(){
  const p = logPath();
  fs.mkdirSync(path.dirname(p), {recursive:true});
  return fs.openSync(p, 'a');
}
function installerRoot(){
  if (process.resourcesPath && fs.existsSync(path.join(process.resourcesPath, 'installer'))) return path.join(process.resourcesPath, 'installer');
  return path.join(__dirname, '..');
}
function runtimeExists(){
  const dir = webuiDir();
  return fs.existsSync(path.join(dir, 'start.sh')) || fs.existsSync(path.join(dir, 'server.py'));
}
function health(){
  return new Promise(resolve => {
    const req = http.get(`${webUrl}/health`, res => { res.resume(); resolve(res.statusCode === 200); });
    req.setTimeout(1500, () => { req.destroy(); resolve(false); });
    req.on('error', () => resolve(false));
  });
}
async function waitForHealth(seconds=35){
  const deadline = Date.now() + seconds * 1000;
  while(Date.now() < deadline){
    if(await health()) return true;
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  return false;
}
function loadSetup(mode){
  return win.loadFile(path.join(__dirname, 'setup.html'), {query: {mode, port, dir: webuiDir()}});
}
function startExistingRuntime(){
  if(!runtimeExists()) return false;
  const dir = webuiDir();
  const logFd = ensureLogFd();
  if(process.platform === 'win32'){
    const command = `cd ~/.hermes/webui/workspace/hermes-for-web && ./start.sh ${port} >> ~/.hermes/logs/hermes-ceo-console.log 2>&1`;
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
    'echo This command window installs or updates the FMG-provided Hermes WebUI runtime,',
    `echo then starts the WebUI at http://127.0.0.1:${port}.`,
    'echo It uses quick setup by default: Codex, Telegram, and Paperclip are skipped here',
    'echo and can be configured later from the WebUI/settings flow.',
    'echo Do not close this window until the setup says it is complete.',
    'echo.',
    'echo [How to proceed]',
    'echo 1. If Windows asks for permission or shows SmartScreen, choose Run/Allow.',
    'echo 2. If WSL2 or Ubuntu is missing, this installer will try to install Ubuntu automatically.',
    'echo    If Windows asks for Administrator permission or a reboot, allow it and rerun setup.',
    'echo 3. If Ubuntu opens for the first time, create the Ubuntu username/password,',
    'echo    then return here and run Setup Wizard again. That second run continues to Hermes install.',
    'echo 4. When Ubuntu is ready, the next stage installs/updates Hermes Agent and FMG WebUI.',
    'echo    This can take several minutes. Keep this window open until it prints Done.',
    'echo 5. The installer skips Codex/Telegram/Paperclip prompts by default.',
    'echo    Open the WebUI first, then configure integrations later from settings.',
    'echo 6. When the setup finishes, go back to the Hermes CEO Console app and press',
    `echo    Retry / Check Again. The app should open http://127.0.0.1:${port}.`,
    'echo.',
    'echo [If nothing seems to happen]',
    'echo - Keep this window open and copy the last visible error line.',
    'echo - App log: %USERPROFILE%\\.hermes\\logs\\hermes-ceo-console.log',
    'echo - You can rerun this file by double-clicking it again.',
    'echo.',
    `powershell.exe -NoExit -NoProfile -ExecutionPolicy Bypass -File ${quoteForCmd(script)} -Port ${quoteForCmd(port)} -Distro ${quoteForCmd(wslDistro)} -Yes -SkipCodex -SkipTelegram -SkipPaperclip -SkipHermesUpdate`,
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
    loadSetup('starting-existing');
    startExistingRuntime();
    if(await waitForHealth(35)) win.loadURL(webUrl);
    else loadSetup('existing-failed');
    return;
  }
  loadSetup('first-run');
}
function createWindow(){
  win = new BrowserWindow({width: 1280, height: 860, title: 'Hermes CEO Console', webPreferences:{preload:path.join(__dirname,'preload.js')}});
  win.webContents.setWindowOpenHandler(({url}) => { shell.openExternal(url); return {action:'deny'}; });
  route();
}
ipcMain.handle('health', health);
ipcMain.handle('runtime-status', async () => ({healthy: await health(), runtimeExists: runtimeExists(), webUrl, webuiDir: webuiDir(), logPath: logPath()}));
ipcMain.handle('open-webui', async () => { await shell.openExternal(webUrl); return true; });
ipcMain.handle('retry', async () => { await route(); return true; });
ipcMain.handle('start-existing', async () => { const started = startExistingRuntime(); return {started, healthy: await waitForHealth(35)}; });
ipcMain.handle('run-setup', async () => runSetup());
ipcMain.handle('open-logs', async () => {
  const p = logPath();
  if(fs.existsSync(p)) await shell.openPath(p); else dialog.showMessageBox({message:'Log file not found yet', detail:p});
  return true;
});
app.whenReady().then(createWindow);
app.on('window-all-closed', ()=>{ if(process.platform !== 'darwin') app.quit(); });
