# iris-dev for VS Code

Wires [iris-agentic-dev](https://github.com/intersystems-community/iris-agentic-dev) MCP tools into VS Code Copilot agent mode. Automatically picks up your `objectscript.conn` connection so your AI assistant can compile, test, search, and debug ObjectScript without leaving the chat.

## Requirements

- VS Code 1.99+
- The [iris-dev binary](https://github.com/intersystems-community/iris-agentic-dev/releases) on PATH (or set `iris-dev.serverPath`)
- The [ObjectScript extension](https://marketplace.visualstudio.com/items?itemName=intersystems-community.vscode-objectscript) with an active connection

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `iris-dev.serverPath` | _(auto)_ | Full path to the iris-dev binary. Leave empty to use PATH. |
| `iris-dev.containerName` | _(empty)_ | Docker container name for tools requiring direct IRIS access. |
| `iris-dev.tlsVerify` | `true` | Verify TLS certificates. Set `false` for self-signed certs. |
| `iris-dev.toolset` | `baseline` | Tool set: `baseline`, `nostub`, or `merged` (includes interop/container tools). |
| `iris-dev.namespace` | _(conn ns)_ | Override the IRIS namespace. Leave empty to use objectscript.conn namespace. |

## Links

- [iris-agentic-dev on GitHub](https://github.com/intersystems-community/iris-agentic-dev)
- [Release notes](https://github.com/intersystems-community/iris-agentic-dev/releases)
