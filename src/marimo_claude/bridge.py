"""Bridge to Marimo's MCP server — async client using the MCP SDK."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

logger = logging.getLogger(__name__)


class MarimoBridge:
    """MCP client that connects to a running Marimo MCP server over HTTP."""

    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._exit_stack: contextlib.AsyncExitStack | None = None
        self._url: str | None = None

    @property
    def connected(self) -> bool:
        return self._session is not None

    async def connect(self, mcp_url: str) -> None:
        if self.connected:
            await self.disconnect()

        self._exit_stack = contextlib.AsyncExitStack()
        try:
            read_stream, write_stream, _ = await self._exit_stack.enter_async_context(
                streamablehttp_client(url=mcp_url)
            )
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self._session.initialize()
            self._url = mcp_url
            logger.info("Connected to Marimo MCP at %s", mcp_url)
        except Exception:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None
            raise

    async def disconnect(self) -> None:
        if self._exit_stack:
            await self._exit_stack.aclose()
        self._session = None
        self._exit_stack = None
        self._url = None

    def _require_connection(self) -> ClientSession:
        if not self._session:
            raise RuntimeError(
                "Not connected to Marimo. Call start_marimo first."
            )
        return self._session

    async def list_tools(self) -> list[dict[str, Any]]:
        session = self._require_connection()
        result = await session.list_tools()
        return [
            {"name": t.name, "description": t.description}
            for t in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        session = self._require_connection()
        result = await session.call_tool(name, arguments or {})
        parts = []
        for content in result.content:
            if isinstance(content, TextContent):
                parts.append(content.text)
            else:
                parts.append(str(content))
        return "\n".join(parts)

    async def list_prompts(self) -> list[dict[str, Any]]:
        session = self._require_connection()
        result = await session.list_prompts()
        return [
            {"name": p.name, "description": p.description}
            for p in result.prompts
        ]

    async def get_prompt(self, name: str, arguments: dict[str, str] | None = None) -> str:
        session = self._require_connection()
        result = await session.get_prompt(name, arguments or {})
        parts = []
        for msg in result.messages:
            if isinstance(msg.content, TextContent):
                parts.append(msg.content.text)
            elif isinstance(msg.content, str):
                parts.append(msg.content)
            else:
                parts.append(str(msg.content))
        return "\n".join(parts)
