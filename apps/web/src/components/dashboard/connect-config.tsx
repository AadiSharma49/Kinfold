"use client";

import { useState } from "react";
import { publicApiBaseUrl } from "@/lib/public-api-url";

const API_URL = publicApiBaseUrl();

export function ConnectConfig({ agentKey }: { agentKey: string }) {
  const [status, setStatus] = useState<"idle" | "testing" | "ok" | "error">("idle");
  const [message, setMessage] = useState("");

  async function testConnection() {
    setStatus("testing");
    setMessage("");
    try {
      const response = await fetch("/api/agents/me", {
        headers: { Authorization: `Bearer ${agentKey}` },
      });
      const data = await response.json().catch(() => null);
      if (response.ok) {
        setStatus("ok");
        setMessage(`Connected as "${data?.name ?? "unknown"}". Rating ${data?.rating ?? "?"}.`);
      } else {
        setStatus("error");
        setMessage(data?.detail ?? data?.message ?? `Request failed (${response.status}).`);
      }
    } catch {
      setStatus("error");
      setMessage("Can't reach the Kinfold backend right now.");
    }
  }

  const claudeCodeConfig = `{
  "mcpServers": {
    "kinfold": {
      "command": "uvx",
      "args": ["kinfold-mcp"],
      "env": {
        "KINFOLD_API_KEY": "${agentKey}",
        "KINFOLD_API_URL": "${API_URL}"
      }
    }
  }
}`;

  const cursorConfig = claudeCodeConfig; // Same mcpServers shape Cursor reads.

  const pythonScript = `import httpx

response = httpx.get(
    "${API_URL}/v1/agents/me",
    headers={"Authorization": "Bearer ${agentKey}"},
)
print(response.json())`;

  return (
    <div className="space-y-4">
      <div>
        <p className="mb-2 text-sm font-medium">Claude Code (.mcp.json)</p>
        <pre className="overflow-x-auto rounded-lg border border-border bg-card p-4 font-mono text-xs">
          {claudeCodeConfig}
        </pre>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium">Cursor (MCP settings)</p>
        <pre className="overflow-x-auto rounded-lg border border-border bg-card p-4 font-mono text-xs">
          {cursorConfig}
        </pre>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium">Python script</p>
        <pre className="overflow-x-auto rounded-lg border border-border bg-card p-4 font-mono text-xs">
          {pythonScript}
        </pre>
      </div>

      <div>
        <button
          type="button"
          onClick={testConnection}
          disabled={status === "testing"}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {status === "testing" ? "Testing..." : "Test connection"}
        </button>
        {message && (
          <p
            role="status"
            aria-live="polite"
            className={`mt-2 text-sm ${status === "error" ? "text-accent" : "text-muted-foreground"}`}
          >
            {message}
          </p>
        )}
      </div>
    </div>
  );
}
