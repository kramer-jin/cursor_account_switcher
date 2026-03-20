const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const net = require("net");
const fs = require("fs");

async function getFreePort(host) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, host, () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

async function waitForOk(url, { timeoutMs = 10000, intervalMs = 200 } = {}) {
  const start = Date.now();
  // Node 18+ / Electron 28 支持全局 fetch
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url, { method: "GET" });
      if (res.ok) return;
    } catch (e) {
      // ignore
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`backend not ready: ${url}`);
}

function createWindow(loadUrl) {
  const win = new BrowserWindow({
    width: 1120,
    height: 760,
    show: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });

  // 防止页面打开新窗口/跳转到外部（降低安全风险）
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));

  win.webContents.on("will-navigate", (event, targetUrl) => {
    // 限制导航到同源
    try {
      const u1 = new URL(loadUrl);
      const u2 = new URL(targetUrl);
      if (u1.origin !== u2.origin) event.preventDefault();
    } catch {
      event.preventDefault();
    }
  });

  win.loadURL(loadUrl);
  return win;
}

function spawnBackend({ host, port }) {
  const backendBinaryName = "CursorAccountSwitcherBackend";

  // electron-builder 的打包结构在不同版本/配置下可能不同：
  // - 期望：Contents/Resources/backend/<bin>
  // - 实际（本次构建）：Contents/Resources/app/resources/backend/<bin>
  const candidates = [
    path.join(process.resourcesPath, "backend", backendBinaryName),
    path.join(process.resourcesPath, "app", "resources", "backend", backendBinaryName),
    path.join(process.resourcesPath, "app", "backend", backendBinaryName)
  ];

  const backendPath = candidates.find((p) => fs.existsSync(p));
  if (!backendPath) {
    throw new Error(`backend binary not found under resources: ${candidates.join(" | ")}`);
  }
  const child = spawn(backendPath, ["--host", host, "--port", String(port)], {
    stdio: ["ignore", "pipe", "pipe"],
    env: process.env
  });

  // 帮助排障：把 backend 输出透出到 electron 主进程控制台
  child.stdout.on("data", (d) => {
    const s = d.toString("utf-8");
    if (s.includes("backend_ready")) {
      // ready line exists; no-op
    }
  });
  child.stderr.on("data", (d) => {
    // eslint-disable-next-line no-console
    console.error(d.toString("utf-8").trim());
  });

  return child;
}

app.on("before-quit", () => {
  // 让 before-quit 更快触发；实际清理在每个 child 上处理
});

app.whenReady().then(async () => {
  const host = "127.0.0.1";

  const port = await getFreePort(host);
  const backend = spawnBackend({ host, port });

  const url = `http://${host}:${port}/`;
  // 轮询一个会访问 sqlite 的接口：后端真正 ready 后会返回 200/500
  // 用 ok() 代表 http server 已经起来（500 也不代表没起来，建议只按 network ok 即可）
  await waitForOk(`${url}api/current`, { timeoutMs: 15000, intervalMs: 250 });

  const win = createWindow(url);

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });

  // Electron 退出时结束后端
  app.on("will-quit", () => {
    try {
      backend.kill("SIGTERM");
    } catch {
      // ignore
    }
  });

  return win;
});

