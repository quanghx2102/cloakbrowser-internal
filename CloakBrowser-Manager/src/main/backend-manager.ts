import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import fs from 'fs';
import axios from 'axios';
import { app, dialog } from 'electron';

export class BackendManager {
  private process: ChildProcess | null = null;
  private port: number = 8080;
  private dataDir: string = '';

  constructor() {
    this.resolveDataDir();
  }

  private resolveDataDir() {
    if (process.env.APP_DATA_DIR) {
      this.dataDir = path.resolve(process.env.APP_DATA_DIR);
      if (!fs.existsSync(this.dataDir)) {
        fs.mkdirSync(this.dataDir, { recursive: true });
      }
      // Create standard subdirectories
      const subDirs = ['profiles', 'database', 'logs', 'backups', 'config', 'browsers'];
      for (const subDir of subDirs) {
        const fullPath = path.join(this.dataDir, subDir);
        if (!fs.existsSync(fullPath)) {
          fs.mkdirSync(fullPath, { recursive: true });
        }
      }
      return;
    }

    const appName = 'CloakInternalTool';
    const oldAppName = 'CloakBrowserManager';
    let oldDataDir = '';

    if (process.platform === 'darwin') {
      this.dataDir = path.join(app.getPath('home'), 'Library', 'Application Support', appName);
      oldDataDir = path.join(app.getPath('home'), 'Library', 'Application Support', oldAppName);
    } else if (process.platform === 'win32') {
      this.dataDir = path.join(process.env.APPDATA || app.getPath('home'), appName);
      oldDataDir = path.join(process.env.APPDATA || app.getPath('home'), oldAppName);
    } else {
      this.dataDir = path.join(app.getPath('home'), '.config', appName.toLowerCase());
      oldDataDir = path.join(app.getPath('home'), '.config', oldAppName.toLowerCase());
    }

    // Migration logic from old app name directory to new directory
    if (fs.existsSync(oldDataDir) && !fs.existsSync(this.dataDir)) {
      console.log(`Migrating existing data from ${oldDataDir} to ${this.dataDir}...`);
      try {
        fs.cpSync(oldDataDir, this.dataDir, { recursive: true });
        console.log('Migration successful!');

        // Also move profiles.db to the database/ subfolder if it is at the root of the migrated folder
        const oldDbPath = path.join(this.dataDir, 'profiles.db');
        const newDbDir = path.join(this.dataDir, 'database');
        if (!fs.existsSync(newDbDir)) {
          fs.mkdirSync(newDbDir, { recursive: true });
        }
        const newDbPath = path.join(newDbDir, 'profiles.db');
        if (fs.existsSync(oldDbPath) && !fs.existsSync(newDbPath)) {
          fs.renameSync(oldDbPath, newDbPath);
          console.log('Moved database file to database/ profiles.db subfolder.');
        }
      } catch (err) {
        console.error('Migration failed:', err);
      }
    }

    if (!fs.existsSync(this.dataDir)) {
      fs.mkdirSync(this.dataDir, { recursive: true });
    }

    // Create standard subdirectories
    const subDirs = ['profiles', 'database', 'logs', 'backups', 'config', 'browsers'];
    for (const subDir of subDirs) {
      const fullPath = path.join(this.dataDir, subDir);
      if (!fs.existsSync(fullPath)) {
        fs.mkdirSync(fullPath, { recursive: true });
      }
    }
  }

  public getConfigFile(): string {
    return path.join(this.dataDir, 'config', 'app-config.json');
  }

  public getSavedBinaryPath(): string | null {
    const configPath = this.getConfigFile();
    if (fs.existsSync(configPath)) {
      try {
        const content = fs.readFileSync(configPath, 'utf8');
        const config = JSON.parse(content);
        return config.cloakbrowser_binary_path || null;
      } catch (e) {
        console.error('Failed to read app-config.json:', e);
      }
    }
    return null;
  }

  public saveBinaryPath(binaryPath: string): void {
    const configPath = this.getConfigFile();
    let config: any = {};
    if (fs.existsSync(configPath)) {
      try {
        config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      } catch (e) {
        // ignore
      }
    }
    config.cloakbrowser_binary_path = binaryPath;
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf8');
  }

  private validateBinaryPath(candidatePath: string): { isValid: boolean; errorCode?: string } {
    if (!fs.existsSync(candidatePath)) {
      return { isValid: false, errorCode: 'CLOAK_BROWSER_BINARY_NOT_FOUND' };
    }
    try {
      const stat = fs.statSync(candidatePath);
      if (stat.isDirectory()) {
        return { isValid: false, errorCode: 'CLOAK_BROWSER_BINARY_INVALID' };
      }
    } catch (e) {
      return { isValid: false, errorCode: 'CLOAK_BROWSER_BINARY_INVALID' };
    }
    if (process.platform !== 'win32') {
      try {
        fs.accessSync(candidatePath, fs.constants.X_OK);
      } catch (err) {
        return { isValid: false, errorCode: 'CLOAK_BROWSER_BINARY_INVALID' };
      }
    }
    return { isValid: true };
  }

  public resolveBinaryPath(): { path: string | null; status: 'Ready' | 'Missing' | 'Invalid'; errorCode?: string } {
    // 1. Env override for dev/debug
    let binaryPath = process.env.CLOAK_BROWSER_BINARY_PATH || process.env.CLOAKBROWSER_BINARY_PATH || null;
    if (binaryPath) {
      const validation = this.validateBinaryPath(binaryPath);
      if (validation.isValid) {
        return { path: binaryPath, status: 'Ready' };
      } else {
        return { path: binaryPath, status: 'Invalid', errorCode: validation.errorCode };
      }
    }

    // 2. Config saved in app-config.json
    binaryPath = this.getSavedBinaryPath();
    if (binaryPath) {
      const validation = this.validateBinaryPath(binaryPath);
      if (validation.isValid) {
        return { path: binaryPath, status: 'Ready' };
      } else {
        return { path: binaryPath, status: 'Invalid', errorCode: validation.errorCode };
      }
    }

    // 3. Auto-detect on macOS
    if (process.platform === 'darwin') {
      const baseDir = path.join(app.getPath('home'), '.cloakbrowser');
      if (fs.existsSync(baseDir)) {
        try {
          const files = fs.readdirSync(baseDir);
          for (const file of files) {
            if (file.startsWith('chromium-')) {
              const candidate = path.join(baseDir, file, 'Chromium.app', 'Contents', 'MacOS', 'Chromium');
              const validation = this.validateBinaryPath(candidate);
              if (validation.isValid) {
                return { path: candidate, status: 'Ready' };
              }
            }
          }
        } catch (e) {
          console.warn('Error scanning for macOS auto-detect binary:', e);
        }
      }
    }

    // 4. Bundled binary in app resources if available
    const candidates: string[] = [];
    const basePaths = [
      process.resourcesPath,
      app.getAppPath(),
      path.join(app.getAppPath(), 'resources')
    ];

    for (const base of basePaths) {
      if (!base) continue;

      const browserBinName = process.platform === 'win32' ? 'cloakbrowser.exe' : 'cloakbrowser';
      candidates.push(path.join(base, 'binaries', browserBinName));

      if (process.platform === 'darwin') {
        candidates.push(path.join(base, 'binaries', 'Chromium.app', 'Contents', 'MacOS', 'Chromium'));

        const binariesDir = path.join(base, 'binaries');
        if (fs.existsSync(binariesDir)) {
          try {
            const files = fs.readdirSync(binariesDir);
            for (const file of files) {
              if (file.startsWith('chromium-')) {
                candidates.push(path.join(binariesDir, file, 'Chromium.app', 'Contents', 'MacOS', 'Chromium'));
              }
            }
          } catch (e) {
            // ignore
          }
        }
      }
    }

    // Deduplicate candidates and check them in order
    const uniqueCandidates = Array.from(new Set(candidates));
    for (const candidate of uniqueCandidates) {
      const validation = this.validateBinaryPath(candidate);
      if (validation.isValid) {
        return { path: candidate, status: 'Ready' };
      }
    }

    return { path: null, status: 'Missing', errorCode: 'CLOAK_BROWSER_BINARY_NOT_CONFIGURED' };
  }

  public getPort(): number {
    return this.port;
  }

  public getDataDir(): string {
    return this.dataDir;
  }

  public async start(port: number): Promise<boolean> {
    this.port = port;
    const isDev = !app.isPackaged;

    let command = '';
    let args: string[] = [];

    const binaryResolution = this.resolveBinaryPath();
    const binaryPath = binaryResolution.path || '';

    // Log data path and binary path
    console.log(`[Lifecycle] APP_DATA_DIR: ${this.dataDir}`);
    console.log(`[Lifecycle] Resolved CloakBrowser Binary: ${binaryPath || 'NONE'} (Status: ${binaryResolution.status})`);

    const env = {
      ...process.env,
      CLOAK_DESKTOP: '1',
      CLOAK_DATA_DIR: this.dataDir,
      PORT: this.port.toString(),
      CLOAK_BROWSER_BINARY_PATH: binaryPath,
    };

    if (isDev) {
      // In development, run using uvicorn module from local virtualenv if present
      const venvBin = process.platform === 'win32' ? 'python.exe' : 'python3';
      const localVenv = path.join(app.getAppPath(), '.venv', 'bin', venvBin);
      const localVenvScripts = path.join(app.getAppPath(), '.venv', 'Scripts', 'python.exe');
      
      if (fs.existsSync(localVenv)) {
        command = localVenv;
      } else if (process.platform === 'win32' && fs.existsSync(localVenvScripts)) {
        command = localVenvScripts;
      } else {
        command = 'python3';
      }
      args = ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', this.port.toString(), '--log-level', 'info'];
    } else {
      // In production, run the packaged binary inside extraResources
      const binaryName = process.platform === 'win32' ? 'backend.exe' : 'backend';
      command = path.join(process.resourcesPath, 'binaries', binaryName);
      args = ['--port', this.port.toString()];

      if (!fs.existsSync(command)) {
        console.error(`Backend binary not found at: ${command}. Falling back to default app directory.`);
        command = path.join(app.getAppPath(), 'backend', 'dist', binaryName);
      }
    }

    console.log(`Starting backend with command: ${command} ${args.join(' ')}`);

    this.process = spawn(command, args, { env, cwd: app.getAppPath() });

    const logFilePath = path.join(this.dataDir, 'logs', 'backend.log');
    const logStream = fs.createWriteStream(logFilePath, { flags: 'a' });

    this.process.stdout?.on('data', (data) => {
      const msg = `[FastAPI stdout]: ${data.toString().trim()}`;
      console.log(msg);
      logStream.write(`[${new Date().toISOString()}] ${msg}\n`);
    });

    this.process.stderr?.on('data', (data) => {
      const msg = `[FastAPI stderr]: ${data.toString().trim()}`;
      console.error(msg);
      logStream.write(`[${new Date().toISOString()}] ${msg}\n`);
    });

    this.process.on('close', (code) => {
      const msg = `FastAPI backend process exited with code ${code}`;
      console.log(msg);
      logStream.write(`[${new Date().toISOString()}] [Lifecycle] ${msg}\n`);
      logStream.end();
      this.process = null;
    });

    // Wait for the backend to start and respond to status ping
    return await this.waitForBackend();
  }

  private async waitForBackend(retries = 30, delayMs = 500): Promise<boolean> {
    const statusUrl = `http://127.0.0.1:${this.port}/api/status`;
    console.log(`Waiting for backend to be ready at ${statusUrl}...`);

    for (let i = 0; i < retries; i++) {
      try {
        const response = await axios.get(statusUrl, { timeout: 1000 });
        if (response.status === 200) {
          console.log('FastAPI backend is ready!');
          return true;
        }
      } catch (err: any) {
        if (i === retries - 1) {
          console.error(`FastAPI backend health check failed at retry ${i + 1}/${retries}: ${err.message || err}`);
        }
      }
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }

    console.error('FastAPI backend startup timed out.');
    return false;
  }

  public async stop(cleanupProfiles: boolean = true) {
    if (!this.process) return;

    console.log('Stopping FastAPI backend process...');
    
    // Handle profile cleanup settings before stopping backend
    if (cleanupProfiles) {
      try {
        await axios.post(`http://127.0.0.1:${this.port}/api/profiles/stop-all`, {}, { timeout: 3000 });
        console.log('Successfully requested profile cleanup.');
      } catch (e) {
        console.warn('Failed to call stop-all API gracefully before killing backend.');
      }
    } else {
      try {
        await axios.post(`http://127.0.0.1:${this.port}/api/profiles/skip-cleanup`, {}, { timeout: 3000 });
        console.log('Successfully requested skip-cleanup from backend.');
      } catch (e) {
        console.warn('Failed to call skip-cleanup API before killing backend.');
      }
    }

    // Kill the backend process
    this.process.kill('SIGINT');
    
    // Wait a brief moment, then force kill if still alive
    await new Promise((resolve) => setTimeout(resolve, 500));
    if (this.process) {
      this.process.kill('SIGKILL');
      this.process = null;
    }
  }
}
