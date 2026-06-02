import { app, BrowserWindow, dialog, ipcMain, Notification } from 'electron';
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
    // mainWindow.webContents.openDevTools();
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

  ipcMain.handle('show-runtime-notification', (_event, data: { title: string; body: string; profileId: string; severity: string }) => {
    const { title, body, severity } = data;
    if (severity !== 'critical') {
      return { success: false, error: 'Only critical notifications allowed' };
    }
    if (!Notification.isSupported()) {
      return { success: false, error: 'Notifications not supported' };
    }
    const notification = new Notification({
      title: title || 'Profile stopped for safety',
      body: body || 'Proxy IP changed unexpectedly'
    });
    notification.show();
    return { success: true };
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

  async function createErrorWindow() {
    mainWindow = new BrowserWindow({
      width: 800,
      height: 600,
      title: 'Lỗi Khởi Động Backend',
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
      },
    });

    const errorHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Lỗi Khởi Động Backend</title>
      <style>
        body {
          background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
          color: #f1f5f9;
          font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          margin: 0;
          padding: 0;
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
        }
        .card {
          background: rgba(30, 41, 59, 0.7);
          backdrop-filter: blur(16px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 16px;
          padding: 40px;
          max-width: 600px;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
          text-align: center;
          animation: fadeIn 0.6s ease-out;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .icon {
          font-size: 64px;
          color: #ef4444;
          margin-bottom: 24px;
        }
        h1 {
          font-size: 24px;
          margin-bottom: 16px;
          font-weight: 700;
          background: linear-gradient(to right, #f43f5e, #fb7185);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        p {
          font-size: 16px;
          line-height: 1.6;
          color: #cbd5e1;
          margin-bottom: 24px;
        }
        .btn {
          background: linear-gradient(90deg, #6366f1 0%, #4f46e5 100%);
          color: white;
          border: none;
          padding: 12px 28px;
          font-size: 15px;
          font-weight: 600;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.3s;
          box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        .btn:hover {
          background: linear-gradient(90deg, #4f46e5 0%, #3730a3 100%);
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
        }
      </style>
    </head>
    <body>
      <div class="card">
        <div class="icon">⚠️</div>
        <h1>Lỗi Khởi Động Backend</h1>
        <p>Local FastAPI Backend Server không thể khởi chạy hoặc không phản hồi sau healthcheck. Vui lòng đảm bảo các cổng kết nối từ 8080-8180 không bị xung đột, các thư mục quyền dữ liệu hợp lệ và python3 đã được cài đặt đầy đủ các dependency (pip install -r backend/requirements.txt).</p>
        <button class="btn" onclick="window.close()">Thoát Ứng Dụng</button>
      </div>
    </body>
    </html>`;

    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(errorHtml));

    mainWindow.on('closed', () => {
      mainWindow = null;
      app.quit();
    });
  }

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
      console.error('Failed to start backend. Displaying error window.');
      createErrorWindow();
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
