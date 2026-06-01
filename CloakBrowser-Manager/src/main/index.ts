import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import path from 'path';
import fs from 'fs';
import findFreePort from 'find-free-port';
import { BackendManager } from './backend-manager';
import { initLogger } from './logger';
import axios from 'axios';

let mainWindow: BrowserWindow | null = null;
const backendManager = new BackendManager();

async function createWindow(port: number) {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    title: 'CloakBrowser Manager',
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const isDev = !app.isPackaged;
  const devUrl = `http://localhost:5173/?api_port=${port}`;
  
  if (isDev) {
    mainWindow.loadURL(devUrl);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(app.getAppPath(), 'frontend', 'dist', 'index.html'), {
      query: { api_port: port.toString() }
    });
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Keep single instance lock
const additionalData = { myKey: 'cloak-browser-manager' };
const gotTheLock = app.requestSingleInstanceLock(additionalData);

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  // Register IPC handlers for CloakBrowser binary management
  ipcMain.handle('get-binary-status', () => {
    return backendManager.resolveBinaryPath();
  });

  ipcMain.handle('save-binary-path', (_event, binaryPath: string) => {
    if (!binaryPath) {
      return { success: false, error: 'Path is empty' };
    }
    if (!fs.existsSync(binaryPath)) {
      return { success: false, error: 'File does not exist' };
    }
    if (process.platform !== 'win32') {
      try {
        fs.accessSync(binaryPath, fs.constants.X_OK);
      } catch (err) {
        return { success: false, error: 'File is not executable' };
      }
    }
    backendManager.saveBinaryPath(binaryPath);
    return { success: true };
  });

  ipcMain.handle('select-binary', async () => {
    const result = await dialog.showOpenDialog({
      title: 'Chọn CloakBrowser Binary',
      properties: ['openFile'],
      filters: [
        {
          name: 'Executables',
          extensions: process.platform === 'win32' ? ['exe'] : ['*']
        }
      ]
    });

    if (result.canceled || result.filePaths.length === 0) {
      return { canceled: true };
    }

    const binaryPath = result.filePaths[0];
    if (process.platform !== 'win32') {
      try {
        fs.accessSync(binaryPath, fs.constants.X_OK);
      } catch (err) {
        try {
          fs.chmodSync(binaryPath, 0o755);
        } catch (chmodErr) {
          return { success: false, error: 'File is not executable and failed to set execute permission' };
        }
      }
    }

    backendManager.saveBinaryPath(binaryPath);
    return { success: true, path: binaryPath };
  });

  // Ensure the backend process is stopped when Electron exits unexpectedly
  process.on('uncaughtException', async (error) => {
    console.error('Uncaught Exception in Electron main process:', error);
    try {
      await backendManager.stop(true);
    } catch (err) {
      console.error('Error stopping backend during uncaught exception:', err);
    }
    app.exit(1);
  });

  process.on('unhandledRejection', async (reason) => {
    console.error('Unhandled Rejection in Electron main process:', reason);
  });

  app.on('ready', async () => {
    // Initialize the desktop logger as soon as logs directory is created/available
    const logsDir = path.join(backendManager.getDataDir(), 'logs');
    initLogger(logsDir);

    console.log('--- Electron Startup ---');
    console.log(`App is ready. APP_DATA_DIR is set to: ${backendManager.getDataDir()}`);
    console.log(`Standard logs directory: ${logsDir}`);
    console.log('Scanning for free port...');
    
    let port = 8080;
    try {
      const freePorts = await findFreePort(8080, 8180, '127.0.0.1');
      if (freePorts && freePorts[0]) {
        port = freePorts[0];
      }
    } catch (err) {
      console.warn('Failed to scan for free port, using default port 8080:', err);
    }

    console.log(`Port allocated: ${port}. Starting FastAPI Backend...`);
    const success = await backendManager.start(port);
    
    if (success) {
      createWindow(port);
    } else {
      console.error('Failed to start backend. Exiting application.');
      // Wait, dialog.showErrorBox was already shown inside backend-manager.ts start method if missing binary!
      // So if start failed and it wasn't a missing binary (e.g. timeout or python missing), show the backend boot fail dialog:
      const browserBinName = process.platform === 'win32' ? 'cloakbrowser.exe' : 'cloakbrowser';
      let bundledBrowserPath = path.join(process.resourcesPath, 'binaries', browserBinName);
      if (!fs.existsSync(bundledBrowserPath)) {
        bundledBrowserPath = path.join(app.getAppPath(), 'binaries', browserBinName);
      }
      const binaryPath = process.env.CLOAK_BROWSER_BINARY_PATH || bundledBrowserPath;

      if (fs.existsSync(binaryPath)) {
        dialog.showErrorBox(
          'Lỗi khởi động Backend',
          'Không thể khởi động FastAPI Backend cục bộ. Vui lòng đảm bảo các dependency Python đã được cài đặt đầy đủ hoặc cài đặt lại ứng dụng.'
        );
      }
      app.quit();
    }
  });

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      app.quit();
    }
  });

  app.on('activate', () => {
    if (mainWindow === null) {
      createWindow(backendManager.getPort());
    }
  });

  let isQuitting = false;
  app.on('before-quit', async (e) => {
    if (isQuitting) return;
    
    console.log('App before-quit triggered. Checking for running profiles...');
    e.preventDefault();
    
    let runningCount = 0;
    try {
      const port = backendManager.getPort();
      const response = await axios.get(`http://127.0.0.1:${port}/api/status`, { timeout: 1000 });
      runningCount = response.data.running_count || 0;
    } catch (err) {
      console.warn('Failed to query running profiles from backend:', err);
    }

    let cleanupProfiles = true;

    if (runningCount > 0) {
      const choice = dialog.showMessageBoxSync({
        type: 'question',
        buttons: ['Đóng tất cả và thoát', 'Giữ trình duyệt tiếp tục chạy và thoát', 'Hủy bỏ'],
        defaultId: 0,
        cancelId: 2,
        title: 'Xác nhận thoát',
        message: `Có ${runningCount} profile trình duyệt đang hoạt động.`,
        detail: 'Bạn muốn xử lý các trình duyệt đang chạy này thế nào?',
      });

      if (choice === 2) {
        console.log('Quit cancelled by user.');
        return;
      }
      cleanupProfiles = choice === 0;
    }

    isQuitting = true;
    console.log('--- Electron Shutdown ---');
    console.log(`Shutting down. cleanupProfiles=${cleanupProfiles}`);
    await backendManager.stop(cleanupProfiles);
    app.exit(0);
  });
}
