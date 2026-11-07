"""MCP stdio client used by the deterministic agent workflow."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, TypeVar

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel


logger = logging.getLogger("nbo.mcp.client")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ModelT = TypeVar("ModelT", bound=BaseModel)


class MCPToolError(RuntimeError):
    """Raised when an MCP tool returns an error or invalid structured output."""


class MCPToolTrace(BaseModel):
    tool: str
    arguments: dict[str, Any]
    status: str
    duration_ms: float
    result: dict[str, Any] | None = None
    error: str | None = None


class MCPClient:
    """One real MCP stdio client session with traceable tool calls."""

    def __init__(self) -> None:
        self._session: ClientSession | None = None
        self._stdio_context: Any = None
        self._session_context: Any = None
        self.traces: list[MCPToolTrace] = []
        self.server_tools: list[str] = []

    async def __aenter__(self) -> "MCPClient":
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "backend.app.mcp.server"],
            cwd=PROJECT_ROOT,
            env=os.environ.copy(),
        )
        self._stdio_context = stdio_client(parameters, errlog=sys.stderr)
        read_stream, write_stream = await self._stdio_context.__aenter__()
        self._session_context = ClientSession(read_stream, write_stream)
        self._session = await self._session_context.__aenter__()
        await self._session.initialize()
        tools_result = await self._session.list_tools()
        self.server_tools = [tool.name for tool in tools_result.tools]
        logger.info("MCP initialized; tools=%s", self.server_tools)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._session_context is not None:
            await self._session_context.__aexit__(exc_type, exc, traceback)
        if self._stdio_context is not None:
            await self._stdio_context.__aexit__(exc_type, exc, traceback)

    async def call_tool(
        self,
        name: str,
        request: BaseModel,
        response_model: type[ModelT],
    ) -> ModelT:
        if self._session is None:
            raise MCPToolError("MCP client session is not initialized.")
        arguments = {"request": request.model_dump(mode="json")}
        started = time.perf_counter()
        try:
            result = await self._session.call_tool(name, arguments=arguments)
            if getattr(result, "is_error", False):
                raise MCPToolError(self._text_result(result))
            payload = getattr(result, "structured_content", None)
            if not isinstance(payload, dict):
                payload = self._parse_text_result(result)
            validated = response_model.model_validate(payload)
        except Exception as error:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            message = str(error)
            self.traces.append(
                MCPToolTrace(
                    tool=name,
                    arguments=arguments,
                    status="error",
                    duration_ms=duration_ms,
                    error=message,
                )
            )
            logger.exception("MCP tool failed: %s", name)
            if isinstance(error, MCPToolError):
                raise
            raise MCPToolError(f"{name} failed: {message}") from error
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        self.traces.append(
            MCPToolTrace(
                tool=name,
                arguments=arguments,
                status="success",
                duration_ms=duration_ms,
                result=validated.model_dump(mode="json"),
            )
        )
        return validated

    @staticmethod
    def _text_result(result: Any) -> str:
        return " ".join(
            getattr(block, "text", "")
            for block in getattr(result, "content", [])
            if getattr(block, "type", None) == "text"
        ) or "MCP tool returned an error."

    @classmethod
    def _parse_text_result(cls, result: Any) -> dict[str, Any]:
        text = cls._text_result(result)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise MCPToolError("MCP tool returned no structured output.") from error
        if not isinstance(payload, dict):
            raise MCPToolError("MCP tool returned a non-object result.")
        return payload
