const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('hermesDesktop', {
  health: () => ipcRenderer.invoke('health'),
  runtimeStatus: () => ipcRenderer.invoke('runtime-status'),
  retry: () => ipcRenderer.invoke('retry'),
  startExisting: () => ipcRenderer.invoke('start-existing'),
  runSetup: () => ipcRenderer.invoke('run-setup'),
  openLogs: () => ipcRenderer.invoke('open-logs'),
  openWebui: () => ipcRenderer.invoke('open-webui'),
  checkUpdates: () => ipcRenderer.invoke('check-updates'),
  restartServer: () => ipcRenderer.invoke('restart-server')
});
