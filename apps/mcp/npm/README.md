# kinfold-mcp (npm)

Launcher for the Kinfold MCP server. `npx kinfold-mcp` runs the Python
package `kinfold-mcp` from PyPI through `uvx kinfold-mcp`, so it needs
[uv](https://docs.astral.sh/uv/) installed. The Python package holds all
the logic; this package only forwards stdio, environment variables, and
the exit code.

Full docs, MCP client configs, and the key setup are in the repository's
`apps/mcp/README.md`.

## Usage

```bash
KINFOLD_API_KEY=kf_live_your_key_here npx kinfold-mcp
```

Or as an MCP server config:

```json
{
  "mcpServers": {
    "kinfold": {
      "command": "npx",
      "args": ["-y", "kinfold-mcp"],
      "env": {
        "KINFOLD_API_KEY": "kf_live_your_key_here"
      }
    }
  }
}
```

## License

Apache-2.0, same as the Python package.
