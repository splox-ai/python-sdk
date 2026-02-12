"""MCP integration tests against live Splox API.

Required env vars:
    SPLOX_API_KEY
Optional env vars:
    SPLOX_BASE_URL            (default: https://app.splox.io/api/v1)
    SPLOX_MCP_SEARCH_QUERY    (default: "")

For execute-tool integration (optional):
    SPLOX_MCP_SERVER_ID
    SPLOX_MCP_TOOL_SLUG
    SPLOX_MCP_TOOL_ARGS_JSON  (default: {})
"""

from __future__ import annotations

import json
import os

import pytest

from splox import AsyncSploxClient, SploxClient


def _normalize_base_url(value: str) -> str:
    base = value.strip()
    if not base:
        return "https://app.splox.io/api/v1"
    if not base.startswith("http://") and not base.startswith("https://"):
        base = "https://" + base
    return base


API_KEY = os.environ.get("SPLOX_API_KEY", "").strip()
BASE_URL = _normalize_base_url(os.environ.get("SPLOX_BASE_URL", "https://app.splox.io/api/v1"))
SEARCH_QUERY = os.environ.get("SPLOX_MCP_SEARCH_QUERY", "")

EXEC_SERVER_ID = os.environ.get("SPLOX_MCP_SERVER_ID", "").strip()
EXEC_TOOL_SLUG = os.environ.get("SPLOX_MCP_TOOL_SLUG", "").strip()
EXEC_TOOL_ARGS = os.environ.get("SPLOX_MCP_TOOL_ARGS_JSON", "{}")


pytestmark = pytest.mark.skipif(
    not API_KEY,
    reason="SPLOX_API_KEY not set",
)


def _parse_tool_args() -> dict:
    try:
        parsed = json.loads(EXEC_TOOL_ARGS)
    except json.JSONDecodeError as exc:
        raise AssertionError("SPLOX_MCP_TOOL_ARGS_JSON must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise AssertionError("SPLOX_MCP_TOOL_ARGS_JSON must decode to an object")
    return parsed


def test_mcp_sync_discovery_integration() -> None:
    with SploxClient(api_key=API_KEY, base_url=BASE_URL) as client:
        catalog = client.mcp.list_catalog(search=SEARCH_QUERY, per_page=10)
        assert catalog.total_count >= 0
        assert isinstance(catalog.mcp_servers, list)

        servers = client.mcp.list_user_servers()
        assert servers.total >= 0
        assert isinstance(servers.servers, list)

        if servers.servers:
            tools = client.mcp.get_server_tools(servers.servers[0].id)
            assert tools.total >= 0
            assert isinstance(tools.options, list)


@pytest.mark.asyncio
async def test_mcp_async_discovery_integration() -> None:
    async with AsyncSploxClient(api_key=API_KEY, base_url=BASE_URL) as client:
        catalog = await client.mcp.list_catalog(search=SEARCH_QUERY, per_page=10)
        assert catalog.total_count >= 0
        assert isinstance(catalog.mcp_servers, list)

        servers = await client.mcp.list_user_servers()
        assert servers.total >= 0
        assert isinstance(servers.servers, list)

        if servers.servers:
            tools = await client.mcp.get_server_tools(servers.servers[0].id)
            assert tools.total >= 0
            assert isinstance(tools.options, list)


def test_mcp_execute_sync_integration() -> None:
    if not EXEC_SERVER_ID or not EXEC_TOOL_SLUG:
        pytest.skip("Set SPLOX_MCP_SERVER_ID and SPLOX_MCP_TOOL_SLUG to run execute integration test")

    args = _parse_tool_args()

    with SploxClient(api_key=API_KEY, base_url=BASE_URL) as client:
        result = client.mcp.execute_tool(
            mcp_server_id=EXEC_SERVER_ID,
            tool_slug=EXEC_TOOL_SLUG,
            args=args,
        )

        assert isinstance(result.is_error, bool)
        assert result.result is not None


@pytest.mark.asyncio
async def test_mcp_execute_async_integration() -> None:
    if not EXEC_SERVER_ID or not EXEC_TOOL_SLUG:
        pytest.skip("Set SPLOX_MCP_SERVER_ID and SPLOX_MCP_TOOL_SLUG to run execute integration test")

    args = _parse_tool_args()

    async with AsyncSploxClient(api_key=API_KEY, base_url=BASE_URL) as client:
        result = await client.mcp.execute_tool(
            mcp_server_id=EXEC_SERVER_ID,
            tool_slug=EXEC_TOOL_SLUG,
            args=args,
        )

        assert isinstance(result.is_error, bool)
        assert result.result is not None
