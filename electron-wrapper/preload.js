const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('hermesDesktop', {
  health: () => ipcRenderer.invoke('health'),
  retry: () => ipcRenderer.invoke('retry'),
  runSetup: () => ipcRenderer.invoke('run-setup'),
  openLogs: () => ipcRenderer.invoke('open-logs'),
  openWebui: () => ipcRenderer.invoke('open-webui')
});
