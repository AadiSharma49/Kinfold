#!/usr/bin/env node
// Launcher: `npx kinfold-mcp` runs the Python server through `uvx
// kinfold-mcp`. All the real logic lives in the Python package; this
// only forwards stdio, env, and the exit code. Requires uv on PATH.

const { spawn } = require("node:child_process");

const child = spawn("uvx", ["kinfold-mcp", ...process.argv.slice(2)], {
  stdio: "inherit",
  env: process.env,
});

child.on("error", (error) => {
  if (error.code === "ENOENT") {
    console.error(
      "kinfold-mcp needs uv installed to run: https://docs.astral.sh/uv/"
    );
  } else {
    console.error(error.message);
  }
  process.exit(1);
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});
