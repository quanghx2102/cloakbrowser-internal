import { contextBridge } from 'electron';

contextBridge.exposeInMainWorld('electron', {
  isDesktop: true,
  platform: process.platform,
  version: process.versions.chrome,
});
