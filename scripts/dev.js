#!/usr/bin/env node
// Dev entrypoint — syncs backend deps, starts services, runs frontend + backend concurrently.
// Cross-platform: works on Windows (cmd/PowerShell/Git Bash) and Linux/macOS.

const { execSync, spawn } = require("child_process");
const path = require("path");
const os = require("os");

const PROJECT_ROOT = path.resolve(__dirname, "..");
const BACKEND_DIR = path.join(PROJECT_ROOT, "backend");
const FRONTEND_DIR = path.join(PROJECT_ROOT, "frontend");
const isWindows = os.platform() === "win32";

// Sync backend dependencies
console.log("[obsidian-webdev] Syncing backend dependencies...");
execSync("uv sync --quiet", { stdio: "inherit", cwd: BACKEND_DIR });

// Start background services (Qdrant)
require("./start-services.js");

const env = { ...process.env, PYTHONUNBUFFERED: "1" };
const shell = isWindows ? true : false;

// Spawn frontend: npm run dev (in frontend/)
const frontend = spawn("npm", ["run", "dev"], {
  cwd: FRONTEND_DIR,
  stdio: "inherit",
  shell,
  env,
});

// Spawn backend: uv run uvicorn ... (in backend/)
const backend = spawn(
  "uv",
  [
    "run", "uvicorn", "main:app",
    "--port", "8100",
    "--reload",
    "--reload-dir", BACKEND_DIR,
    "--reload-exclude", path.join(BACKEND_DIR, ".venv"),
    "--reload-exclude", path.join(BACKEND_DIR, "data"),
    "--ws-ping-interval", "120",
    "--ws-ping-timeout", "30",
  ],
  {
    cwd: BACKEND_DIR,
    stdio: "inherit",
    shell,
    env,
  },
);

function shutdown() {
  console.log("\n[obsidian-webdev] Shutting down...");
  frontend.kill();
  backend.kill();
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

frontend.on("exit", (code) => {
  if (code !== 0) { backend.kill(); process.exit(code ?? 0); }
});
backend.on("exit", (code) => {
  if (code !== 0) { frontend.kill(); process.exit(code ?? 0); }
});
