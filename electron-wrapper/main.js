const { app, BrowserWindow, shell, ipcMain, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');

const port = process.env.HERMES_WEBUI_PORT || '8788';
const webUrl = `http://127.0.0.1:${port}`;
let win = null;
let child = null;

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
    child = spawn('wsl.exe', ['bash', '-lc', command], {stdio:['ignore', logFd, logFd], detached:true});
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
function quoteForPowerShellSingle(s){ return `'${String(s).replace(/'/g, "''")}'`; }
function runSetup(){
  const root = installerRoot();
  const isWin = process.platform === 'win32';
  const script = isWin ? path.join(root, 'install-windows.ps1') : path.join(root, 'install-macos.sh');
  if(!fs.existsSync(script)){
    dialog.showErrorBox('Installer missing', script);
    return {started:false, error:'installer_missing', script};
  }
  if(isWin){
    // Electron GUI apps on Windows do not have a parent console. Start a new
    // visible PowerShell process from PowerShell itself. This avoids `cmd start`
    // title/path parsing bugs where Windows may try to execute the window title
    // (for example: "Hermes CEO Console Setup") as a command.
    const psArgs = [
      '-NoExit',
      '-NoProfile',
      '-ExecutionPolicy', 'Bypass',
      '-File', script,
      '-Port', String(port),
    ];
    const argList = psArgs.map(quoteForPowerShellSingle).join(',');
    const command = `Start-Process -FilePath 'powershell.exe' -ArgumentList @(${argList}) -WindowStyle Normal`;
    child = spawn('powershell.exe', ['-NoProfile','-ExecutionPolicy','Bypass','-Command', command], {detached:true, stdio:'ignore', windowsHide:false});
    child.unref();
    return {started:true, mode:'windows-visible-powershell', script};
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
