import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electron', {
  isDesktop: true,
  platform: process.platform,
  version: process.versions.chrome,
  getBinaryStatus: () => ipcRenderer.invoke('get-binary-status'),
  selectBinary: () => ipcRenderer.invoke('select-binary'),
  saveBinaryPath: (path: string) => ipcRenderer.invoke('save-binary-path'),
  showRuntimeNotification: (data: { title: string; body: string; profileId: string; severity: string }) =>
    ipcRenderer.invoke('show-runtime-notification', data),
});
