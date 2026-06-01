import fs from 'fs';
import path from 'path';

let logStream: fs.WriteStream | null = null;

export function maskSecrets(message: string): string {
  if (!message) return '';
  // 1. Mask proxy URLs with credentials: http://user:pass@host:port -> http://***:***@host:port
  let masked = message.replace(/(https?:\/\/|socks5:\/\/)([^:]+):([^@]+)@/g, '$1***:***@');
  
  // 2. Mask explicit key-value patterns (tokens, passwords, secrets) in logs
  masked = masked.replace(/(token|password|auth|secret|key)["'\s:]+([a-zA-Z0-9_\-\.]+)/gi, (match, p1, p2) => {
    // Keep the key, replace the value with ***
    return `${p1}": "***"`;
  });

  return masked;
}

export function initLogger(logsDir: string) {
  try {
    const logPath = path.join(logsDir, 'desktop.log');
    logStream = fs.createWriteStream(logPath, { flags: 'a' });
    
    // Override console.log and console.error
    const originalLog = console.log;
    const originalError = console.error;
    
    console.log = (...args: any[]) => {
      const rawMessage = args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ');
      const maskedMessage = maskSecrets(rawMessage);
      originalLog.apply(console, [maskedMessage]);
      writeToLogFile('INFO', maskedMessage);
    };

    console.error = (...args: any[]) => {
      const rawMessage = args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ');
      const maskedMessage = maskSecrets(rawMessage);
      originalError.apply(console, [maskedMessage]);
      writeToLogFile('ERROR', maskedMessage);
    };

    console.log('--- Custom Desktop Logger Initialized ---');
  } catch (err) {
    // Fallback if logger initialization fails
    console.error('Failed to initialize desktop.log writer:', err);
  }
}

function writeToLogFile(level: string, message: string) {
  if (logStream) {
    const timestamp = new Date().toISOString();
    logStream.write(`[${timestamp}] [${level}] ${message}\n`);
  }
}
