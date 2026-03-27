"""Marimo subprocess management — start/stop notebook editor with MCP enabled."""

from __future__ import annotations

import asyncio
import logging
import shutil

logger = logging.getLogger(__name__)

# Default port for Marimo editor
DEFAULT_PORT = 2718


class MarimoProcess:
    """Manages a Marimo editor subprocess."""

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._port: int = DEFAULT_PORT
        self._notebook_path: str | None = None

    @property
    def url(self) -> str | None:
        if self.running:
            return f"http://localhost:{self._port}"
        return None

    @property
    def mcp_url(self) -> str | None:
        if self.running:
            return f"http://localhost:{self._port}/mcp/server"
        return None

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def start(
        self,
        notebook_path: str | None = None,
        port: int = DEFAULT_PORT,
        host: str = "127.0.0.1",
    ) -> str:
        if self.running:
            return f"Marimo already running at {self.url}"

        marimo_bin = shutil.which("marimo")
        if not marimo_bin:
            raise RuntimeError("marimo not found in PATH. Install with: uv add marimo")

        cmd = [marimo_bin, "edit"]
        if notebook_path:
            cmd.append(notebook_path)
        cmd.extend([
            "--port", str(port),
            "--host", host,
            "--headless",
            "--no-token",
            "--skip-update-check",
            "--mcp",
        ])

        logger.info("Starting Marimo: %s", " ".join(cmd))
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._port = port
        self._notebook_path = notebook_path

        # Wait for Marimo to become ready
        await self._wait_for_ready()

        logger.info("Marimo started at %s (MCP: %s)", self.url, self.mcp_url)
        return self.url

    async def _wait_for_ready(self, timeout: float = 15.0) -> None:
        """Wait for Marimo to print its URL, indicating it's ready."""
        import httpx

        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            if self._process.returncode is not None:
                stderr = b""
                if self._process.stderr:
                    stderr = await self._process.stderr.read()
                raise RuntimeError(f"Marimo exited with code {self._process.returncode}: {stderr.decode()}")
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"http://localhost:{self._port}/health", timeout=1.0)
                    if resp.status_code == 200:
                        return
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(0.5)

        raise RuntimeError(f"Marimo did not become ready within {timeout}s")

    async def stop(self) -> str:
        if not self.running:
            return "Marimo is not running"

        url = self.url
        self._process.terminate()
        try:
            await asyncio.wait_for(self._process.wait(), timeout=5)
        except asyncio.TimeoutError:
            self._process.kill()
            await self._process.wait()

        self._process = None
        self._notebook_path = None
        logger.info("Marimo stopped (was at %s)", url)
        return f"Marimo stopped (was at {url})"
