# marimo-claude

MCP server that bridges [Marimo](https://marimo.io) notebooks and Claude — edit, inspect, and visualize notebooks collaboratively.

## What it does

- **Starts/stops Marimo** as a managed subprocess with MCP enabled
- **Bridges MCP protocols**: stdio (for Claude Code/Desktop) ↔ HTTP (Marimo's MCP server)
- **Inspects running notebooks**: cells, variables, DataFrames, errors, database schemas
- **Shows notebooks** as interactive iframes in Claude Desktop via [mcp-ui-server](https://mcpui.dev)
- **Reads notebook files** directly (.py format)

## Architecture

```
Claude Code (stdio) ──→ marimo-claude (MCP Server) ──httpx──→ Marimo (HTTP MCP)
Claude Desktop (stdio) ─┘          │
                                   ├── mcp-ui-server → Notebook as iframe in client
                                   └── Process management (start/stop Marimo)
```

## Installation

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
# Clone and install
git clone https://github.com/synapticore-io/marimo-claude.git
cd marimo-claude
uv sync
```

### Claude Code Plugin

```bash
claude --plugin-dir /path/to/marimo-claude
```

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "marimo-claude": {
      "command": "uv",
      "args": ["--directory", "/path/to/marimo-claude", "run", "marimo-claude"]
    }
  }
}
```

### Standalone MCP Server

```bash
uv run marimo-claude
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `start_marimo` | Start Marimo editor with MCP enabled |
| `stop_marimo` | Stop the running Marimo instance |
| `marimo_status` | Check if Marimo is running |
| `show_notebook` | Display notebook as interactive iframe |
| `list_notebooks` | List active notebook sessions |
| `get_cells` | Read cell structure and code |
| `get_variables` | Inspect variables and DataFrames |
| `get_cell_data` | Get runtime data (execution status, outputs) |
| `get_database_schema` | Inspect database schemas |
| `get_errors` | Error summary across sessions |
| `read_notebook` | Read a .py notebook file |
| `list_marimo_tools` | Discover available Marimo MCP tools |

## Usage

1. Ask Claude to start a notebook: *"Start a Marimo notebook"*
2. Claude calls `start_marimo` → Marimo launches with MCP
3. Inspect and edit: *"Show me the variables in the notebook"*
4. Visualize: *"Show the notebook"* → iframe in Claude Desktop

## License

MIT
