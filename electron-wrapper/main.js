const { app, BrowserWindow, shell, ipcMain, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');

const port = process.env.HERMES_WEBUI_PORT || '8788';
const webUrl = `http://127.0.0.1:${port}`;
let win = null;
let child = null;

function installerRoot(){
  if (process.resourcesPath && fs.existsSync(path.join(process.resourcesPath, 'installer'))) return path.join(process.resourcesPath, 'installer');
  return path.join(__dirname, '..');
}
function health(){
  return new Promise(resolve => {
    const req = http.get(`${webUrl}/health`, res => { res.resume(); resolve(res.statusCode === 200); });
    req.setTimeout(1500, () => { req.destroy(); resolve(false); });
    req.on('error', () => resolve(false));
  });
}
function runSetup(){
  const root = installerRoot();
  const isWin = process.platform === 'win32';
  const script = isWin ? path.join(root, 'install-windows.ps1') : path.join(root, 'install-macos.sh');
  if(!fs.existsSync(script)){
    dialog.showErrorBox('Installer missing', script);
    return;
  }
  if(isWin){
    child = spawn('powershell.exe', ['-ExecutionPolicy','Bypass','-File',script,'-Port',port], {stdio:'ignore', detached:true});
  } else {
    child = spawn('/bin/bash', [script, '--port', port], {stdio:'ignore', detached:true});
  }
  child.unref();
}
async function route(){
  if(await health()) win.loadURL(webUrl); else win.loadFile(path.join(__dirname, 'setup.html'));
}
function createWindow(){
  win = new BrowserWindow({width: 1280, height: 860, title: 'Hermes CEO Console', webPreferences:{preload:path.join(__dirname,'preload.js')}});
  win.webContents.setWindowOpenHandler(({url}) => { shell.openExternal(url); return {action:'deny'}; });
  route();
}
ipcMain.handle('health', health);
ipcMain.handle('open-webui', async () => { await shell.openExternal(webUrl); return true; });
ipcMain.handle('retry', async () => { await route(); return true; });
ipcMain.handle('run-setup', async () => { runSetup(); return true; });
ipcMain.handle('open-logs', async () => {
  const log = process.platform === 'win32' ? path.join(app.getPath('home'), '.hermes','logs','hermes-ceo-console.log') : path.join(app.getPath('home'), '.hermes','logs','hermes-ceo-console.log');
  if(fs.existsSync(log)) await shell.openPath(log); else dialog.showMessageBox({message:'Log file not found yet', detail:log});
  return true;
});
app.whenReady().then(createWindow);
app.on('window-all-closed', ()=>{ if(process.platform !== 'darwin') app.quit(); });
