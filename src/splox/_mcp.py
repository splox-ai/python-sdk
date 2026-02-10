"""MCP catalog, connections, and connection token utilities."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import time
from typing import Any, Dict, Optional

from splox._models import (
    MCPCatalogItem,
    MCPCatalogListResponse,
    MCPConnection,
    MCPConnectionListResponse,
)
from splox._transport import AsyncTransport, SyncTransport

# ---------------------------------------------------------------------------
# Connection token constants
# ---------------------------------------------------------------------------

_MCP_CONNECTION_ISSUER = "splox-mcp-connection"
_MCP_CONNECTION_EXPIRY_SECONDS = 60 * 60  # 1 hour


# ---------------------------------------------------------------------------
# JWT helpers (standalone, no external dependency)
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    """Base64-URL encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _derive_signing_key(credentials_encryption_key: str) -> bytes:
    """Derive the HMAC-SHA256 signing key from the credentials encryption key.

    This mirrors the backend ``deriveSigningKey`` function --- SHA-256 of
    ``"mcp-connection-jwt:" + credentials_encryption_key``.
    """
    return hashlib.sha256(
        ("mcp-connection-jwt:" + credentials_encryption_key).encode()
    ).digest()


def generate_connection_token(
    mcp_server_id: str,
    owner_user_id: str,
    end_user_id: str,
    credentials_encryption_key: str,
) -> str:
    """Generate a signed HS256 JWT for end-user credential submission.

    This is the client-side equivalent of the backend's
    ``mcp.GenerateConnectionToken``. The token expires after 1 hour.

    Args:
        mcp_server_id: UUID of the MCP catalog server.
        owner_user_id: UUID of the platform owner/user.
        end_user_id: Identifier of the end-user.
        credentials_encryption_key: The shared credentials encryption key.

    Returns:
        A signed JWT string.
    """
    now = int(time.time())

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "mcp_server_id": mcp_server_id,
        "owner_user_id": owner_user_id,
        "end_user_id": end_user_id,
        "iss": _MCP_CONNECTION_ISSUER,
        "iat": now,
        "exp": now + _MCP_CONNECTION_EXPIRY_SECONDS,
    }

    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}"

    key = _derive_signing_key(credentials_encryption_key)
    signature = hmac.new(key, signing_input.encode(), hashlib.sha256).digest()

    return f"{signing_input}.{_b64url_encode(signature)}"


def generate_connection_link(
    base_url: str,
    mcp_server_id: str,
    owner_user_id: str,
    end_user_id: str,
    credentials_encryption_key: str,
) -> str:
    """Build a full connection URL for end-user credential submission.

    Args:
        base_url: The Splox application URL (e.g. ``"https://app.splox.io"``).
        mcp_server_id: UUID of the MCP catalog server.
        owner_user_id: UUID of the platform owner/user.
        end_user_id: Identifier of the end-user.
        credentials_encryption_key: The shared credentials encryption key.

    Returns:
        A URL string like ``https://app.splox.io/tools/connect?token=...``.
    """
    token = generate_connection_token(
        mcp_server_id, owner_user_id, end_user_id, credentials_encryption_key
    )
    return f"{base_url.rstrip('/')}/tools/connect?token={token}"


# ---------------------------------------------------------------------------
# Sync MCP resource
# ---------------------------------------------------------------------------


class MCP:
    """Synchronous MCP catalog and connection operations."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    # -- Catalog ------------------------------------------------------------

    def list_catalog(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        featured: bool = False,
    ) -> MCPCatalogListResponse:
        """List MCP servers from the catalog.

        Args:
            page: Page number (default 1).
            per_page: Items per page (1-100, default 20).
            search: Search by name, description, or URL.
            featured: Only return featured servers.

        Returns:
            MCPCatalogListResponse with servers and pagination metadata.
        """
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if search is not None:
            params["search"] = search
        if featured:
            params["featured"] = "true"

        data = self._t.request("GET", "/mcp-catalog", params=params)
        return MCPCatalogListResponse.from_dict(data)

    def get_catalog_item(self, item_id: str) -> MCPCatalogItem:
        """Get a single MCP server from the catalog by ID.

        Args:
            item_id: UUID of the catalog item.

        Returns:
            MCPCatalogItem.
        """
        data = self._t.request("GET", f"/mcp-catalog/{item_id}")
        return MCPCatalogItem.from_dict(data.get("mcp_server", data))

    # -- Connections --------------------------------------------------------

    def list_connections(
        self,
        *,
        mcp_server_id: Optional[str] = None,
        end_user_id: Optional[str] = None,
    ) -> MCPConnectionListResponse:
        """List MCP connections for the authenticated user.

        Args:
            mcp_server_id: Optional filter by MCP server UUID.
            end_user_id: Optional filter by end-user identifier.

        Returns:
            MCPConnectionListResponse with connections and total count.
        """
        params: Dict[str, Any] = {}
        if mcp_server_id is not None:
            params["mcp_server_id"] = mcp_server_id
        if end_user_id is not None:
            params["end_user_id"] = end_user_id

        data = self._t.request("GET", "/mcp-connections", params=params)
        return MCPConnectionListResponse.from_dict(data)

    def delete_connection(self, connection_id: str) -> None:
        """Delete an end-user MCP connection by ID.

        Args:
            connection_id: UUID of the connection to delete.
        """
        self._t.request("DELETE", f"/mcp-connections/{connection_id}")

    # -- Token helpers (convenience wrappers) --------------------------------

    @staticmethod
    def generate_connection_token(
        mcp_server_id: str,
        owner_user_id: str,
        end_user_id: str,
        credentials_encryption_key: str,
    ) -> str:
        """Generate a signed JWT for end-user credential submission.

        See :func:`generate_connection_token` for details.
        """
        return generate_connection_token(
            mcp_server_id, owner_user_id, end_user_id, credentials_encryption_key
        )

    @staticmethod
    def generate_connection_link(
        base_url: str,
        mcp_server_id: str,
        owner_user_id: str,
        end_user_id: str,
        credentials_encryption_key: str,
    ) -> str:
        """Build a full connection URL for end-user credential submission.

        See :func:`generate_connection_link` for details.
        """
        return generate_connection_link(
            base_url, mcp_server_id, owner_user_id, end_user_id, credentials_encryption_key
        )


# ---------------------------------------------------------------------------
# Async MCP resource
# ---------------------------------------------------------------------------


class AsyncMCP:
    """Asynchronous MCP catalog and connection operations."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    # -- Catalog ------------------------------------------------------------

    async def list_catalog(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        featured: bool = False,
    ) -> MCPCatalogListResponse:
        """List MCP servers from the catalog.

        Args:
            page: Page number (default 1).
            per_page: Items per page (1-100, default 20).
            search: Search by name, description, or URL.
            featured: Only return featured servers.

        Returns:
            MCPCatalogListResponse with servers and pagination metadata.
        """
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if search is not None:
            params["search"] = search
        if featured:
            params["featured"] = "true"

        data = await self._t.request("GET", "/mcp-catalog", params=params)
        return MCPCatalogListResponse.from_dict(data)

    async def get_catalog_item(self, item_id: str) -> MCPCatalogItem:
        """Get a single MCP server from the catalog by ID.

        Args:
            item_id: UUID of the catalog item.

        Returns:
            MCPCatalogItem.
        """
        data = await self._t.request("GET", f"/mcp-catalog/{item_id}")
        return MCPCatalogItem.from_dict(data.get("mcp_server", data))

    # -- Connections --------------------------------------------------------

    async def list_connections(
        self,
        *,
        mcp_server_id: Optional[str] = None,
        end_user_id: Optional[str] = None,
    ) -> MCPConnectionListResponse:
        """List MCP connections for the authenticated user.

        Args:
            mcp_server_id: Optional filter by MCP server UUID.
            end_user_id: Optional filter by end-user identifier.

        Returns:
            MCPConnectionListResponse with connections and total count.
        """
        params: Dict[str, Any] = {}
        if mcp_server_id is not None:
            params["mcp_server_id"] = mcp_server_id
        if end_user_id is not None:
            params["end_user_id"] = end_user_id

        data = await self._t.request("GET", "/mcp-connections", params=params)
        return MCPConnectionListResponse.from_dict(data)

    async def delete_connection(self, connection_id: str) -> None:
        """Delete an end-user MCP connection by ID.

        Args:
            connection_id: UUID of the connection to delete.
        """
        await self._t.request("DELETE", f"/mcp-connections/{connection_id}")

    # -- Token helpers (convenience wrappers) --------------------------------

    @staticmethod
    def generate_connection_token(
        mcp_server_id: str,
        owner_user_id: str,
        end_user_id: str,
        credentials_encryption_key: str,
    ) -> str:
        """Generate a signed JWT for end-user credential submission.

        See :func:`generate_connection_token` for details.
        """
        return generate_connection_token(
            mcp_server_id, owner_user_id, end_user_id, credentials_encryption_key
        )

    @staticmethod
    def generate_connection_link(
        base_url: str,
        mcp_server_id: str,
        owner_user_id: str,
        end_user_id: str,
        credentials_encryption_key: str,
    ) -> str:
        """Build a full connection URL for end-user credential submission.

        See :func:`generate_connection_link` for details.
        """
        return generate_connection_link(
            base_url, mcp_server_id, owner_user_id, end_user_id, credentials_encryption_key
        )
