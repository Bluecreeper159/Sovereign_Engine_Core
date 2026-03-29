const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const fs = require('fs');

app.disableHardwareAcceleration();

let mainWindow;
let backendProcess = null;

const IS_WIN    = process.platform === 'win32';
const IS_PACKED = app.isPackaged;

// Source files — read-only inside AppImage squashfs
const RESOURCE_BACKEND = IS_PACKED
  ? path.join(process.resourcesPath, 'backend')
  : path.resolve(__dirname, '..');

// Writable working dir — always writable regardless of packaging
const WORKING_DIR = IS_PACKED
  ? path.join(app.getPath('userData'), 'engine')
  : path.resolve(__dirname, '..');

const VENV_PYTHON = path.join(
  WORKING_DIR, '.venv',
  IS_WIN ? 'Scripts/python.exe' : 'bin/python3'
);

let TARGET_PORT = 8002;
let TARGET_URL  = `http://127.0.0.1:${TARGET_PORT}/`;

// ── Port finder ───────────────────────────────────────────
function findFreePort(start, cb) {
  const s = net.createServer();
  s.listen(start, '127.0.0.1', () => { const p = s.address().port; s.close(() => cb(p)); });
  s.on('error', () => findFreePort(start + 1, cb));
}

// ── Window ────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400, height: 860,
    minWidth: 900, minHeight: 600,
    title: 'Sovereign // engine runtime',
    webPreferences: { nodeIntegration: false, contextIsolation: true },
    backgroundColor: '#080c09',
  });

  mainWindow.setMenuBarVisibility(false);
  mainWindow.loadURL(TARGET_URL);

  // Retry until backend is up
  mainWindow.webContents.on('did-fail-load', (e, code, desc) => {
    if (code === 0) return;
    console.log(`[SOVEREIGN] Load failed (${code}). Retrying in 1.5s...`);
    setTimeout(() => {
      if (mainWindow && !mainWindow.isDestroyed()) mainWindow.loadURL(TARGET_URL);
    }, 1500);
  });
}

// ── First-run: copy read-only resources to writable dir ───
function extractBackend(cb) {
  console.log(`[SOVEREIGN] First run — extracting backend to: ${WORKING_DIR}`);
  try {
    fs.mkdirSync(WORKING_DIR, { recursive: true });
    // Copy source files. Skip .venv / .env if already present (preserves user config on reinstall)
    fs.cpSync(RESOURCE_BACKEND, WORKING_DIR, {
      recursive: true,
      filter: (src) => {
        const rel = path.relative(RESOURCE_BACKEND, src);
        if (rel.startsWith('.venv')) return false;
        if (rel === '.env') return !fs.existsSync(path.join(WORKING_DIR, '.env'));
        return true;
      }
    });
    console.log('[SOVEREIGN] Backend extracted.');
  } catch (err) {
    console.error('[SOVEREIGN] Extract error:', err.message);
  }
  cb();
}

// ── Install venv if missing ───────────────────────────────
function runInstall(cb) {
  console.log('[SOVEREIGN] Installing dependencies...');
  const cmd = IS_WIN ? ['cmd.exe', ['/c', 'install.bat']] : ['/bin/bash', ['install.sh']];
  const proc = spawn(cmd[0], cmd[1], { cwd: WORKING_DIR, stdio: 'inherit' });
  proc.on('close', cb);
  proc.on('error', (err) => { console.error('[SOVEREIGN] Install error:', err.message); cb(); });
}

// ── Start backend guardian ────────────────────────────────
function startBackend(port) {
  TARGET_PORT = port;
  TARGET_URL  = `http://127.0.0.1:${port}/`;

  const env = Object.assign({}, process.env, { SOV_PORT: String(port), SOV_ELECTRON: '1' });
  const cmd = IS_WIN ? ['cmd.exe', ['/c', 'start.bat']] : ['/bin/bash', ['start.sh']];

  console.log(`[SOVEREIGN] Starting backend on port ${port} from: ${WORKING_DIR}`);
  backendProcess = spawn(cmd[0], cmd[1], { cwd: WORKING_DIR, stdio: 'inherit', env });
  backendProcess.on('error', (err) => console.error('[SOVEREIGN] Backend error:', err.message));

  // Give guardian time to bind before opening window
  setTimeout(createWindow, 4000);
}

// ── Boot sequence ─────────────────────────────────────────
function boot() {
  findFreePort(8002, (port) => {
    const needsExtract = IS_PACKED && !fs.existsSync(path.join(WORKING_DIR, 'start.sh'));
    const needsInstall = !fs.existsSync(VENV_PYTHON);

    if (needsExtract) {
      extractBackend(() => runInstall(() => startBackend(port)));
    } else if (needsInstall) {
      runInstall(() => startBackend(port));
    } else {
      startBackend(port);
    }
  });
}

app.whenReady().then(boot);

app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});
