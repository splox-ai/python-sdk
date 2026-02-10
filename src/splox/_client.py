"""Splox client — sync and async flavors."""

from __future__ import annotations

import os
from typing import Optional

from splox._resources import (
    AsyncChats,
    AsyncEvents,
    AsyncMemory,
    AsyncWorkflows,
    AsyncBilling,
    Billing,
    Chats,
    Events,
    Memory,
    Workflows,
)
from splox._mcp import AsyncMCP, MCP
from splox._transport import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, AsyncTransport, SyncTransport


class SploxClient:
    """Synchronous Splox API client.

    Usage::

        from splox import SploxClient

        client = SploxClient(api_key="your-api-key")
        chat = client.chats.create(name="Session", resource_id="wf-id")
        result = client.workflows.run(
            workflow_version_id="ver-id",
            chat_id=chat.id,
            start_node_id="node-id",
            query="Hello",
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the Splox client.

        Args:
            api_key: API token. Falls back to ``SPLOX_API_KEY`` env var.
            base_url: API base URL (default: ``https://app.splox.io/api/v1``).
            timeout: Request timeout in seconds (default: 30).
        """
        resolved_key = api_key or os.environ.get("SPLOX_API_KEY")
        self._transport = SyncTransport(
            base_url=base_url,
            api_key=resolved_key,
            timeout=timeout,
        )
        self.workflows = Workflows(self._transport)
        self.chats = Chats(self._transport)
        self.events = Events(self._transport)
        self.billing = Billing(self._transport)
        self.memory = Memory(self._transport)
        self.mcp = MCP(self._transport)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._transport.close()

    def __enter__(self) -> SploxClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class AsyncSploxClient:
    """Asynchronous Splox API client.

    Usage::

        from splox import AsyncSploxClient

        async with AsyncSploxClient(api_key="your-api-key") as client:
            chat = await client.chats.create(name="Session", resource_id="wf-id")
            result = await client.workflows.run(
                workflow_version_id="ver-id",
                chat_id=chat.id,
                start_node_id="node-id",
                query="Hello",
            )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the async Splox client.

        Args:
            api_key: API token. Falls back to ``SPLOX_API_KEY`` env var.
            base_url: API base URL (default: ``https://app.splox.io/api/v1``).
            timeout: Request timeout in seconds (default: 30).
        """
        resolved_key = api_key or os.environ.get("SPLOX_API_KEY")
        self._transport = AsyncTransport(
            base_url=base_url,
            api_key=resolved_key,
            timeout=timeout,
        )
        self.workflows = AsyncWorkflows(self._transport)
        self.chats = AsyncChats(self._transport)
        self.events = AsyncEvents(self._transport)
        self.billing = AsyncBilling(self._transport)
        self.memory = AsyncMemory(self._transport)
        self.mcp = AsyncMCP(self._transport)

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._transport.close()

    async def __aenter__(self) -> AsyncSploxClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
