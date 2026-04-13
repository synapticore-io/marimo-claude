"""FastMCP server exposing Marimo notebook tools to Claude."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp_ui_server import create_ui_resource
from mcp_ui_server.core import UIResource
from mcp_ui_server.types import UIMetadataKey

from marimo_claude.bridge import MarimoBridge
from marimo_claude.process import MarimoProcess

logger = logging.getLogger(__name__)

# Shared state
_process = MarimoProcess()
_bridge = MarimoBridge()


@asynccontextmanager
async def lifespan(server: FastMCP):
    logger.info("marimo-claude MCP server starting")
    yield
    # Cleanup: stop Marimo and disconnect bridge
    if _bridge.connected:
        await _bridge.disconnect()
    if _process.running:
        await _process.stop()
    logger.info("marimo-claude MCP server stopped")


mcp = FastMCP(
    "marimo-claude",
    instructions=(
        "MCP server for collaborative Marimo notebook editing. "
        "Use start_marimo to launch a notebook, then inspect and edit cells, "
        "view variables, and show the notebook UI."
    ),
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Process management tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def start_marimo(
    notebook_path: str | None = None,
    port: int = 2718,
) -> str:
    """Start a Marimo notebook editor with MCP enabled.

    Args:
        notebook_path: Path to a .py notebook file. Creates new if not exists.
        port: Port for the Marimo web server (default 2718).
    """
    url = await _process.start(notebook_path=notebook_path, port=port)
    await _bridge.connect(_process.mcp_url)
    return f"Marimo running at {url}\nMCP connected at {_process.mcp_url}"


@mcp.tool()
async def stop_marimo() -> str:
    """Stop the running Marimo notebook editor."""
    if _bridge.connected:
        await _bridge.disconnect()
    return await _process.stop()


@mcp.tool()
async def marimo_status() -> str:
    """Check if Marimo is running and the MCP bridge is connected."""
    parts = []
    if _process.running:
        parts.append(f"Marimo: running at {_process.url}")
        parts.append(f"MCP endpoint: {_process.mcp_url}")
        parts.append(f"Bridge: {'connected' if _bridge.connected else 'disconnected'}")
    else:
        parts.append("Marimo: not running")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# UI display tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def show_notebook() -> list[UIResource]:
    """Show the running Marimo notebook as an interactive iframe.

    Opens the Marimo editor UI directly in the Claude client.
    Requires Marimo to be running (call start_marimo first).
    """
    if not _process.running:
        error_html = (
            "<div style='font-family:sans-serif;padding:2rem;color:#c0392b'>"
            "<h2>Marimo not running</h2>"
            "<p>Call <code>start_marimo</code> first to launch a notebook.</p>"
            "</div>"
        )
        return [create_ui_resource({
            "uri": "ui://marimo-claude/error",
            "content": {"type": "rawHtml", "htmlString": error_html},
            "encoding": "text",
        })]

    return [create_ui_resource({
        "uri": "ui://marimo-claude/notebook",
        "content": {"type": "externalUrl", "iframeUrl": _process.url},
        "encoding": "text",
        "uiMetadata": {
            UIMetadataKey.PREFERRED_FRAME_SIZE: ["100%", "80vh"],
        },
    })]


# ---------------------------------------------------------------------------
# Notebook inspection tools (via Marimo MCP bridge)
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_notebooks() -> str:
    """List active Marimo notebook sessions with their file paths."""
    return await _bridge.call_tool("get_active_notebooks")


@mcp.tool()
async def get_cells(session_id: str) -> str:
    """Get the cell structure and code of a notebook session.

    Args:
        session_id: The session ID from list_notebooks.
    """
    return await _bridge.call_tool("get_lightweight_cell_map", {"session_id": session_id})


@mcp.tool()
async def get_variables(session_id: str) -> str:
    """Get variables, DataFrames, and their types from a running notebook.

    Args:
        session_id: The session ID from list_notebooks.
    """
    return await _bridge.call_tool("get_tables_and_variables", {"session_id": session_id})


@mcp.tool()
async def get_cell_data(session_id: str) -> str:
    """Get runtime data for all cells — execution status, outputs, errors.

    Args:
        session_id: The session ID from list_notebooks.
    """
    return await _bridge.call_tool("get_cell_runtime_data", {"session_id": session_id})


@mcp.tool()
async def get_database_schema(session_id: str) -> str:
    """Inspect database table schemas accessible from the notebook.

    Args:
        session_id: The session ID from list_notebooks.
    """
    return await _bridge.call_tool("get_database_tables", {"session_id": session_id})


@mcp.tool()
async def get_errors() -> str:
    """Get an error summary across all active notebook sessions."""
    return await _bridge.get_prompt("errors_summary")


# ---------------------------------------------------------------------------
# Notebook file tools (direct file access, no bridge needed)
# ---------------------------------------------------------------------------

@mcp.tool()
async def read_notebook(notebook_path: str) -> str:
    """Read a Marimo notebook .py file and return its contents.

    Args:
        notebook_path: Path to the .py notebook file.
    """
    path = Path(notebook_path)
    if not path.exists():
        raise FileNotFoundError(f"Notebook not found: {path}")
    if not path.suffix == ".py":
        raise ValueError(f"Expected .py file, got: {path.suffix}")
    return path.read_text(encoding="utf-8")


@mcp.tool()
async def list_marimo_tools() -> str:
    """List all tools available on the connected Marimo MCP server.

    Useful for discovering what Marimo exposes beyond the standard tools.
    """
    tools = await _bridge.list_tools()
    lines = [f"- {t['name']}: {t['description']}" for t in tools]
    return "\n".join(lines) if lines else "No tools found"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
