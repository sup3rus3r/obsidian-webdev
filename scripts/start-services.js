#!/usr/bin/env node
// Start Qdrant for local dev. Idempotent — safe to run if already up.
// Cross-platform: works on Windows and Linux/macOS.

const { execSync } = require("child_process");

function docker(args) {
  return execSync(`docker ${args}`, { encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] }).trim();
}

function startContainer(name, runArgs) {
  try {
    const running = docker(`ps -q -f "name=^/${name}$"`);
    if (running) {
      console.log(`[services] ${name} already running`);
      return;
    }
  } catch { /* ignore */ }

  try {
    const stopped = docker(`ps -aq -f "name=^/${name}$"`);
    if (stopped) {
      console.log(`[services] Restarting stopped ${name} container`);
      execSync(`docker start ${name}`, { stdio: "inherit" });
      return;
    }
  } catch { /* ignore */ }

  console.log(`[services] Creating ${name} container`);
  execSync(`docker run -d --name ${name} --restart unless-stopped ${runArgs}`, { stdio: "inherit" });
}

startContainer(
  "obsidian-qdrant",
  "-p 6333:6333 -v obsidian_qdrant_data:/qdrant/storage qdrant/qdrant:latest",
);

console.log("[services] All services up");
