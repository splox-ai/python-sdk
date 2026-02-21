"""Resource namespaces for the Splox API — Workflows, Chats, Events."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

from splox._models import (
    Chat,
    ChatHistoryResponse,
    ChatListResponse,
    ChatMessage,
    EndUserSecretsSummary,
    EventResponse,
    ExecutionTreeResponse,
    GenerateSecretsLinkResponse,
    HistoryResponse,
    MemoryActionResponse,
    MemoryGetResponse,
    MemoryListResponse,
    RunResponse,
    SSEEvent,
    SecretActionResponse,
    StartNodesResponse,
    WorkflowFull,
    WorkflowListResponse,
    WorkflowRequestFile,
    WorkflowSecretMetadata,
    WorkflowVersion,
    WorkflowVersionListResponse,
    UserBalance,
    TransactionHistoryResponse,
    ActivityStats,
    DailyActivityResponse,
    ChatCompletion,
)
from splox._transport import AsyncTransport, SyncTransport
from splox.exceptions import SploxTimeoutError


# ---------------------------------------------------------------------------
# Workflows (sync)
# ---------------------------------------------------------------------------


class Workflows:
    """Synchronous workflow operations."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        search: Optional[str] = None,
    ) -> WorkflowListResponse:
        """List all workflows for the authenticated user.

        Args:
            limit: Items per page (1-100, default 20).
            cursor: Pagination cursor from previous response.
            search: Search string to filter by name/description.

        Returns:
            WorkflowListResponse with workflows and pagination.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if search is not None:
            params["search"] = search

        data = self._t.request("GET", "/workflows", params=params)
        return WorkflowListResponse.from_dict(data)

    def get(self, workflow_id: str) -> WorkflowFull:
        """Get a workflow with its draft version, nodes, and edges.

        Args:
            workflow_id: The workflow ID.

        Returns:
            WorkflowFull with workflow, version, nodes, and edges.
        """
        data = self._t.request("GET", f"/workflows/{workflow_id}")
        return WorkflowFull.from_dict(data)

    def get_latest_version(self, workflow_id: str) -> WorkflowVersion:
        """Get the latest version of a workflow.

        Args:
            workflow_id: The workflow ID.

        Returns:
            WorkflowVersion for the latest version.
        """
        data = self._t.request("GET", f"/workflows/{workflow_id}/versions/latest")
        return WorkflowVersion.from_dict(data)

    def get_start_nodes(self, workflow_version_id: str) -> StartNodesResponse:
        """Get start nodes for a workflow version.

        Args:
            workflow_version_id: The workflow version ID.

        Returns:
            StartNodesResponse with the list of start nodes.
        """
        data = self._t.request("GET", f"/workflows/{workflow_version_id}/start-nodes")
        return StartNodesResponse.from_dict(data)

    def list_versions(self, workflow_id: str) -> WorkflowVersionListResponse:
        """List all versions of a workflow.

        Args:
            workflow_id: The workflow ID.

        Returns:
            WorkflowVersionListResponse with all versions.
        """
        data = self._t.request("GET", f"/workflows/{workflow_id}/versions")
        return WorkflowVersionListResponse.from_dict(data)

    def run(
        self,
        *,
        workflow_version_id: str,
        chat_id: str,
        start_node_id: str,
        query: str,
        files: Optional[List[WorkflowRequestFile]] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        end_user_id: Optional[str] = None,
    ) -> RunResponse:
        """Trigger a workflow execution.

        Args:
            workflow_version_id: ID of the workflow version to execute.
            chat_id: Chat session ID.
            start_node_id: ID of the Start node to begin execution at.
            query: The user message or query text.
            files: Optional file attachments.
            additional_params: Optional extra parameters.
            end_user_id: Optional identifier for the end-user (for per-user MCP credentials).

        Returns:
            RunResponse with the workflow_request_id.
        """
        body: Dict[str, Any] = {
            "workflow_version_id": workflow_version_id,
            "chat_id": chat_id,
            "start_node_id": start_node_id,
            "query": query,
        }
        if files is not None:
            body["files"] = [f.to_dict() for f in files]
        if additional_params is not None:
            body["additional_params"] = additional_params
        if end_user_id is not None:
            body["end_user_id"] = end_user_id

        data = self._t.request("POST", "/workflow-requests/run", json_body=body)
        return RunResponse.from_dict(data)

    def listen(self, workflow_request_id: str) -> Iterator[SSEEvent]:
        """Stream real-time execution updates via SSE.

        Args:
            workflow_request_id: ID of the workflow request.

        Yields:
            SSEEvent objects with workflow_request and/or node_execution data.
        """
        return self._t.stream_sse(f"/workflow-requests/{workflow_request_id}/listen")

    def get_execution_tree(self, workflow_request_id: str) -> ExecutionTreeResponse:
        """Get the complete execution hierarchy.

        Args:
            workflow_request_id: ID of the workflow request.

        Returns:
            ExecutionTreeResponse containing the full execution tree.
        """
        data = self._t.request("GET", f"/workflow-requests/{workflow_request_id}/execution-tree")
        return ExecutionTreeResponse.from_dict(data)

    def get_history(
        self,
        workflow_request_id: str,
        *,
        limit: int = 10,
        cursor: Optional[str] = None,
        search: Optional[str] = None,
    ) -> HistoryResponse:
        """Get paginated execution history.

        Args:
            workflow_request_id: ID of the workflow request.
            limit: Items per page (max 100).
            cursor: Pagination cursor from previous response.
            search: Search string to filter results.

        Returns:
            HistoryResponse with data and pagination info.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if search is not None:
            params["search"] = search

        data = self._t.request(
            "GET", f"/workflow-requests/{workflow_request_id}/history", params=params
        )
        return HistoryResponse.from_dict(data)

    def stop(self, workflow_request_id: str) -> None:
        """Stop a running workflow execution.

        Args:
            workflow_request_id: ID of the workflow request to stop.
        """
        self._t.request("POST", f"/workflow-requests/{workflow_request_id}/stop")

    def run_and_wait(
        self,
        *,
        workflow_version_id: str,
        chat_id: str,
        start_node_id: str,
        query: str,
        files: Optional[List[WorkflowRequestFile]] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        end_user_id: Optional[str] = None,
        timeout: float = 300.0,
        poll_interval: float = 2.0,
    ) -> ExecutionTreeResponse:
        """Run a workflow and wait for it to complete.

        Convenience method that triggers a run, polls via SSE, then returns
        the full execution tree.

        Args:
            workflow_version_id: ID of the workflow version to execute.
            chat_id: Chat session ID.
            start_node_id: ID of the Start node.
            query: The user message or query text.
            files: Optional file attachments.
            additional_params: Optional extra parameters.
            end_user_id: Optional identifier for the end-user (for per-user MCP credentials).
            timeout: Max seconds to wait (default 300).
            poll_interval: Unused (SSE is real-time), kept for compatibility.

        Returns:
            ExecutionTreeResponse with the completed execution tree.

        Raises:
            SploxTimeoutError: If the workflow doesn't complete within timeout.
        """
        result = self.run(
            workflow_version_id=workflow_version_id,
            chat_id=chat_id,
            start_node_id=start_node_id,
            query=query,
            files=files,
            additional_params=additional_params,
            end_user_id=end_user_id,
        )

        terminal_statuses = {"completed", "failed", "stopped"}
        start_time = time.monotonic()

        for event in self.listen(result.workflow_request_id):
            if time.monotonic() - start_time > timeout:
                raise SploxTimeoutError(
                    f"Workflow did not complete within {timeout}s"
                )
            if (
                event.workflow_request
                and event.workflow_request.status in terminal_statuses
            ):
                break

        return self.get_execution_tree(result.workflow_request_id)

    # -- Secrets -----------------------------------------------------------

    def list_secrets(
        self,
        workflow_id: str,
        *,
        end_user_id: Optional[str] = None,
    ) -> List[WorkflowSecretMetadata]:
        """List secret keys for a workflow (values are never returned).

        Args:
            workflow_id: The workflow ID.
            end_user_id: If set, list secrets for this end-user instead of builder secrets.

        Returns:
            List of secret metadata objects.
        """
        params: Dict[str, Any] = {}
        if end_user_id is not None:
            params["end_user_id"] = end_user_id
        data = self._t.request("GET", f"/workflows/{workflow_id}/secrets", params=params)
        return [WorkflowSecretMetadata.from_dict(s) for s in data]

    def set_env_secret(
        self,
        workflow_id: str,
        *,
        key: str,
        value: str,
        end_user_id: Optional[str] = None,
    ) -> SecretActionResponse:
        """Create or update an environment-variable secret.

        Args:
            workflow_id: The workflow ID.
            key: Secret key name.
            value: Secret value (will be encrypted at rest).
            end_user_id: If set, store as an end-user secret.

        Returns:
            SecretActionResponse confirming the operation.
        """
        body: Dict[str, Any] = {"key": key, "value": value}
        if end_user_id is not None:
            body["end_user_id"] = end_user_id
        data = self._t.request("POST", f"/workflows/{workflow_id}/secrets/env", json_body=body)
        return SecretActionResponse.from_dict(data)

    def set_file_secret(
        self,
        workflow_id: str,
        *,
        key: str,
        s3_url: str,
        end_user_id: Optional[str] = None,
    ) -> SecretActionResponse:
        """Create or update a file-type secret (S3 URL).

        Args:
            workflow_id: The workflow ID.
            key: Secret key name.
            s3_url: S3 URL where the file is stored.
            end_user_id: If set, store as an end-user secret.

        Returns:
            SecretActionResponse confirming the operation.
        """
        body: Dict[str, Any] = {"key": key, "s3_url": s3_url}
        if end_user_id is not None:
            body["end_user_id"] = end_user_id
        data = self._t.request("POST", f"/workflows/{workflow_id}/secrets/file", json_body=body)
        return SecretActionResponse.from_dict(data)

    def delete_secret(
        self,
        workflow_id: str,
        key: str,
        *,
        end_user_id: Optional[str] = None,
    ) -> SecretActionResponse:
        """Delete a secret from a workflow.

        Args:
            workflow_id: The workflow ID.
            key: Secret key to delete.
            end_user_id: If set, delete the end-user's secret instead of the builder secret.

        Returns:
            SecretActionResponse confirming the operation.
        """
        params: Dict[str, Any] = {}
        if end_user_id is not None:
            params["end_user_id"] = end_user_id
        data = self._t.request("DELETE", f"/workflows/{workflow_id}/secrets/{key}", params=params)
        return SecretActionResponse.from_dict(data)

    def list_end_user_secrets(
        self,
        workflow_id: str,
    ) -> List[EndUserSecretsSummary]:
        """List all end-user secrets grouped by end_user_id.

        Args:
            workflow_id: The workflow ID.

        Returns:
            List of EndUserSecretsSummary, one per end-user.
        """
        data = self._t.request("GET", f"/workflows/{workflow_id}/secrets/end-users")
        return [EndUserSecretsSummary.from_dict(s) for s in data]

    def generate_secrets_link(
        self,
        workflow_id: str,
        *,
        end_user_id: str,
    ) -> GenerateSecretsLinkResponse:
        """Generate a public link for an end-user to submit secrets.

        Args:
            workflow_id: The workflow ID.
            end_user_id: Identifier for the end-user.

        Returns:
            GenerateSecretsLinkResponse with the link, token, and expiry.
        """
        body = {"end_user_id": end_user_id}
        data = self._t.request("POST", f"/workflows/{workflow_id}/secrets/generate-link", json_body=body)
        return GenerateSecretsLinkResponse.from_dict(data)


# ---------------------------------------------------------------------------
# Workflows (async)
# ---------------------------------------------------------------------------


class AsyncWorkflows:
    """Asynchronous workflow operations."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(
        self,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
        search: Optional[str] = None,
    ) -> WorkflowListResponse:
        """List all workflows for the authenticated user.

        Args:
            limit: Items per page (1-100, default 20).
            cursor: Pagination cursor from previous response.
            search: Search string to filter by name/description.

        Returns:
            WorkflowListResponse with workflows and pagination.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if search is not None:
            params["search"] = search

        data = await self._t.request("GET", "/workflows", params=params)
        return WorkflowListResponse.from_dict(data)

    async def get(self, workflow_id: str) -> WorkflowFull:
        """Get a workflow with its draft version, nodes, and edges.

        Args:
            workflow_id: The workflow ID.

        Returns:
            WorkflowFull with workflow, version, nodes, and edges.
        """
        data = await self._t.request("GET", f"/workflows/{workflow_id}")
        return WorkflowFull.from_dict(data)

    async def get_latest_version(self, workflow_id: str) -> WorkflowVersion:
        """Get the latest version of a workflow.

        Args:
            workflow_id: The workflow ID.

        Returns:
            WorkflowVersion for the latest version.
        """
        data = await self._t.request("GET", f"/workflows/{workflow_id}/versions/latest")
        return WorkflowVersion.from_dict(data)

    async def get_start_nodes(self, workflow_version_id: str) -> StartNodesResponse:
        """Get start nodes for a workflow version.

        Args:
            workflow_version_id: The workflow version ID.

        Returns:
            StartNodesResponse with the list of start nodes.
        """
        data = await self._t.request("GET", f"/workflows/{workflow_version_id}/start-nodes")
        return StartNodesResponse.from_dict(data)

    async def list_versions(self, workflow_id: str) -> WorkflowVersionListResponse:
        """List all versions of a workflow.

        Args:
            workflow_id: The workflow ID.

        Returns:
            WorkflowVersionListResponse with all versions.
        """
        data = await self._t.request("GET", f"/workflows/{workflow_id}/versions")
        return WorkflowVersionListResponse.from_dict(data)

    async def run(
        self,
        *,
        workflow_version_id: str,
        chat_id: str,
        start_node_id: str,
        query: str,
        files: Optional[List[WorkflowRequestFile]] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        end_user_id: Optional[str] = None,
    ) -> RunResponse:
        """Trigger a workflow execution.

        Args:
            workflow_version_id: ID of the workflow version to execute.
            chat_id: Chat session ID.
            start_node_id: ID of the Start node to begin execution at.
            query: The user message or query text.
            files: Optional file attachments.
            additional_params: Optional extra parameters.
            end_user_id: Optional identifier for the end-user (for per-user MCP credentials).

        Returns:
            RunResponse with the workflow_request_id.
        """
        body: Dict[str, Any] = {
            "workflow_version_id": workflow_version_id,
            "chat_id": chat_id,
            "start_node_id": start_node_id,
            "query": query,
        }
        if files is not None:
            body["files"] = [f.to_dict() for f in files]
        if additional_params is not None:
            body["additional_params"] = additional_params
        if end_user_id is not None:
            body["end_user_id"] = end_user_id

        data = await self._t.request("POST", "/workflow-requests/run", json_body=body)
        return RunResponse.from_dict(data)

    async def listen(self, workflow_request_id: str) -> AsyncIterator[SSEEvent]:
        """Stream real-time execution updates via SSE.

        Args:
            workflow_request_id: ID of the workflow request.

        Yields:
            SSEEvent objects with workflow_request and/or node_execution data.
        """
        async for event in self._t.stream_sse(
            f"/workflow-requests/{workflow_request_id}/listen"
        ):
            yield event

    async def get_execution_tree(self, workflow_request_id: str) -> ExecutionTreeResponse:
        """Get the complete execution hierarchy.

        Args:
            workflow_request_id: ID of the workflow request.

        Returns:
            ExecutionTreeResponse containing the full execution tree.
        """
        data = await self._t.request(
            "GET", f"/workflow-requests/{workflow_request_id}/execution-tree"
        )
        return ExecutionTreeResponse.from_dict(data)

    async def get_history(
        self,
        workflow_request_id: str,
        *,
        limit: int = 10,
        cursor: Optional[str] = None,
        search: Optional[str] = None,
    ) -> HistoryResponse:
        """Get paginated execution history.

        Args:
            workflow_request_id: ID of the workflow request.
            limit: Items per page (max 100).
            cursor: Pagination cursor from previous response.
            search: Search string to filter results.

        Returns:
            HistoryResponse with data and pagination info.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if search is not None:
            params["search"] = search

        data = await self._t.request(
            "GET", f"/workflow-requests/{workflow_request_id}/history", params=params
        )
        return HistoryResponse.from_dict(data)

    async def stop(self, workflow_request_id: str) -> None:
        """Stop a running workflow execution.

        Args:
            workflow_request_id: ID of the workflow request to stop.
        """
        await self._t.request("POST", f"/workflow-requests/{workflow_request_id}/stop")

    async def run_and_wait(
        self,
        *,
        workflow_version_id: str,
        chat_id: str,
        start_node_id: str,
        query: str,
        files: Optional[List[WorkflowRequestFile]] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        end_user_id: Optional[str] = None,
        timeout: float = 300.0,
    ) -> ExecutionTreeResponse:
        """Run a workflow and wait for it to complete.

        Args:
            workflow_version_id: ID of the workflow version to execute.
            chat_id: Chat session ID.
            start_node_id: ID of the Start node.
            query: The user message or query text.
            files: Optional file attachments.
            additional_params: Optional extra parameters.
            end_user_id: Optional identifier for the end-user (for per-user MCP credentials).
            timeout: Max seconds to wait (default 300).

        Returns:
            ExecutionTreeResponse with the completed execution tree.

        Raises:
            SploxTimeoutError: If the workflow doesn't complete within timeout.
        """
        import asyncio

        result = await self.run(
            workflow_version_id=workflow_version_id,
            chat_id=chat_id,
            start_node_id=start_node_id,
            query=query,
            files=files,
            additional_params=additional_params,
            end_user_id=end_user_id,
        )

        terminal_statuses = {"completed", "failed", "stopped"}
        start_time = time.monotonic()

        async for event in self.listen(result.workflow_request_id):
            if time.monotonic() - start_time > timeout:
                raise SploxTimeoutError(
                    f"Workflow did not complete within {timeout}s"
                )
            if (
                event.workflow_request
                and event.workflow_request.status in terminal_statuses
            ):
                break

        return await self.get_execution_tree(result.workflow_request_id)

    # -- Secrets -----------------------------------------------------------

    async def list_secrets(
        self,
        workflow_id: str,
        *,
        end_user_id: Optional[str] = None,
    ) -> List[WorkflowSecretMetadata]:
        """List secret keys for a workflow (values are never returned).

        Args:
            workflow_id: The workflow ID.
            end_user_id: If set, list secrets for this end-user instead of builder secrets.

        Returns:
            List of secret metadata objects.
        """
        params: Dict[str, Any] = {}
        if end_user_id is not None:
            params["end_user_id"] = end_user_id
        data = await self._t.request("GET", f"/workflows/{workflow_id}/secrets", params=params)
        return [WorkflowSecretMetadata.from_dict(s) for s in data]

    async def set_env_secret(
        self,
        workflow_id: str,
        *,
        key: str,
        value: str,
        end_user_id: Optional[str] = None,
    ) -> SecretActionResponse:
        """Create or update an environment-variable secret.

        Args:
            workflow_id: The workflow ID.
            key: Secret key name.
            value: Secret value (will be encrypted at rest).
            end_user_id: If set, store as an end-user secret.

        Returns:
            SecretActionResponse confirming the operation.
        """
        body: Dict[str, Any] = {"key": key, "value": value}
        if end_user_id is not None:
            body["end_user_id"] = end_user_id
        data = await self._t.request("POST", f"/workflows/{workflow_id}/secrets/env", json_body=body)
        return SecretActionResponse.from_dict(data)

    async def set_file_secret(
        self,
        workflow_id: str,
        *,
        key: str,
        s3_url: str,
        end_user_id: Optional[str] = None,
    ) -> SecretActionResponse:
        """Create or update a file-type secret (S3 URL).

        Args:
            workflow_id: The workflow ID.
            key: Secret key name.
            s3_url: S3 URL where the file is stored.
            end_user_id: If set, store as an end-user secret.

        Returns:
            SecretActionResponse confirming the operation.
        """
        body: Dict[str, Any] = {"key": key, "s3_url": s3_url}
        if end_user_id is not None:
            body["end_user_id"] = end_user_id
        data = await self._t.request("POST", f"/workflows/{workflow_id}/secrets/file", json_body=body)
        return SecretActionResponse.from_dict(data)

    async def delete_secret(
        self,
        workflow_id: str,
        key: str,
        *,
        end_user_id: Optional[str] = None,
    ) -> SecretActionResponse:
        """Delete a secret from a workflow.

        Args:
            workflow_id: The workflow ID.
            key: Secret key to delete.
            end_user_id: If set, delete the end-user's secret instead of the builder secret.

        Returns:
            SecretActionResponse confirming the operation.
        """
        params: Dict[str, Any] = {}
        if end_user_id is not None:
            params["end_user_id"] = end_user_id
        data = await self._t.request("DELETE", f"/workflows/{workflow_id}/secrets/{key}", params=params)
        return SecretActionResponse.from_dict(data)

    async def list_end_user_secrets(
        self,
        workflow_id: str,
    ) -> List[EndUserSecretsSummary]:
        """List all end-user secrets grouped by end_user_id.

        Args:
            workflow_id: The workflow ID.

        Returns:
            List of EndUserSecretsSummary, one per end-user.
        """
        data = await self._t.request("GET", f"/workflows/{workflow_id}/secrets/end-users")
        return [EndUserSecretsSummary.from_dict(s) for s in data]

    async def generate_secrets_link(
        self,
        workflow_id: str,
        *,
        end_user_id: str,
    ) -> GenerateSecretsLinkResponse:
        """Generate a public link for an end-user to submit secrets.

        Args:
            workflow_id: The workflow ID.
            end_user_id: Identifier for the end-user.

        Returns:
            GenerateSecretsLinkResponse with the link, token, and expiry.
        """
        body = {"end_user_id": end_user_id}
        data = await self._t.request("POST", f"/workflows/{workflow_id}/secrets/generate-link", json_body=body)
        return GenerateSecretsLinkResponse.from_dict(data)


# ---------------------------------------------------------------------------
# Chats (sync)
# ---------------------------------------------------------------------------


class Chats:
    """Synchronous chat operations."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def create(
        self,
        *,
        name: str,
        resource_id: str,
        resource_type: str = "api",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Chat:
        """Create a new chat session.

        Args:
            name: Display name for the chat session.
            resource_id: ID of the resource (workflow ID, agent ID, etc.).
            resource_type: Type of resource (default: "api").
            metadata: Optional metadata.

        Returns:
            Chat object with the created session.
        """
        body: Dict[str, Any] = {
            "name": name,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }
        if metadata is not None:
            body["metadata"] = metadata

        data = self._t.request("POST", "/chats", json_body=body)
        return Chat.from_dict(data)

    def get(self, chat_id: str) -> Chat:
        """Get a chat session by ID.

        Args:
            chat_id: The chat ID.

        Returns:
            Chat object.
        """
        data = self._t.request("GET", f"/chats/{chat_id}")
        return Chat.from_dict(data)

    def listen(self, chat_id: str) -> Iterator[SSEEvent]:
        """Stream real-time chat events via SSE.

        Args:
            chat_id: The chat ID.

        Yields:
            SSEEvent objects with chat event data.
        """
        return self._t.stream_sse(f"/chat-internal-messages/{chat_id}/listen")

    def list_for_resource(
        self,
        resource_type: str,
        resource_id: str,
    ) -> ChatListResponse:
        """List chats for a specific resource.

        Args:
            resource_type: Resource type ("workflow", "api", "agent", "gui").
            resource_id: The resource ID.

        Returns:
            ChatListResponse with the list of chats.
        """
        data = self._t.request("GET", f"/chats/{resource_type}/{resource_id}")
        return ChatListResponse.from_dict(data)

    def delete(self, chat_id: str) -> None:
        """Delete a chat session.

        Args:
            chat_id: The chat ID to delete.
        """
        self._t.request("DELETE", f"/chats/{chat_id}")

    def get_history(
        self,
        chat_id: str,
        *,
        limit: int = 50,
        before: Optional[str] = None,
    ) -> ChatHistoryResponse:
        """Get paginated chat message history.

        Args:
            chat_id: The chat ID.
            limit: Messages per page (max 200, default 50).
            before: RFC3339 timestamp cursor for backward pagination.
                    Omit to get the latest messages.

        Returns:
            ChatHistoryResponse with messages list and has_more flag.
        """
        params: Dict[str, Any] = {"limit": limit}
        if before is not None:
            params["before"] = before
        data = self._t.request("GET", f"/chat-history/{chat_id}/paginated", params=params)
        return ChatHistoryResponse.from_dict(data)

    def delete_history(self, chat_id: str) -> None:
        """Delete all message history for a chat.

        Args:
            chat_id: The chat ID.
        """
        self._t.request("DELETE", f"/chat-history/{chat_id}")


# ---------------------------------------------------------------------------
# Chats (async)
# ---------------------------------------------------------------------------


class AsyncChats:
    """Asynchronous chat operations."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def create(
        self,
        *,
        name: str,
        resource_id: str,
        resource_type: str = "api",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Chat:
        """Create a new chat session.

        Args:
            name: Display name for the chat session.
            resource_id: ID of the resource (workflow ID, agent ID, etc.).
            resource_type: Type of resource (default: "api").
            metadata: Optional metadata.

        Returns:
            Chat object with the created session.
        """
        body: Dict[str, Any] = {
            "name": name,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }
        if metadata is not None:
            body["metadata"] = metadata

        data = await self._t.request("POST", "/chats", json_body=body)
        return Chat.from_dict(data)

    async def get(self, chat_id: str) -> Chat:
        """Get a chat session by ID.

        Args:
            chat_id: The chat ID.

        Returns:
            Chat object.
        """
        data = await self._t.request("GET", f"/chats/{chat_id}")
        return Chat.from_dict(data)

    async def listen(self, chat_id: str) -> AsyncIterator[SSEEvent]:
        """Stream real-time chat events via SSE.

        Args:
            chat_id: The chat ID.

        Yields:
            SSEEvent objects with chat event data.
        """
        async for event in self._t.stream_sse(
            f"/chat-internal-messages/{chat_id}/listen"
        ):
            yield event

    async def list_for_resource(
        self,
        resource_type: str,
        resource_id: str,
    ) -> ChatListResponse:
        """List chats for a specific resource.

        Args:
            resource_type: Resource type ("workflow", "api", "agent", "gui").
            resource_id: The resource ID.

        Returns:
            ChatListResponse with the list of chats.
        """
        data = await self._t.request("GET", f"/chats/{resource_type}/{resource_id}")
        return ChatListResponse.from_dict(data)

    async def delete(self, chat_id: str) -> None:
        """Delete a chat session.

        Args:
            chat_id: The chat ID to delete.
        """
        await self._t.request("DELETE", f"/chats/{chat_id}")

    async def get_history(
        self,
        chat_id: str,
        *,
        limit: int = 50,
        before: Optional[str] = None,
    ) -> ChatHistoryResponse:
        """Get paginated chat message history.

        Args:
            chat_id: The chat ID.
            limit: Messages per page (max 200, default 50).
            before: RFC3339 timestamp cursor for backward pagination.
                    Omit to get the latest messages.

        Returns:
            ChatHistoryResponse with messages list and has_more flag.
        """
        params: Dict[str, Any] = {"limit": limit}
        if before is not None:
            params["before"] = before
        data = await self._t.request("GET", f"/chat-history/{chat_id}/paginated", params=params)
        return ChatHistoryResponse.from_dict(data)

    async def delete_history(self, chat_id: str) -> None:
        """Delete all message history for a chat.

        Args:
            chat_id: The chat ID.
        """
        await self._t.request("DELETE", f"/chat-history/{chat_id}")


# ---------------------------------------------------------------------------
# Events (sync)
# ---------------------------------------------------------------------------


class Events:
    """Synchronous event/webhook operations."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def send(
        self,
        *,
        webhook_id: str,
        payload: Optional[Dict[str, Any]] = None,
        secret: Optional[str] = None,
    ) -> EventResponse:
        """Send an event via webhook.

        Args:
            webhook_id: The webhook ID.
            payload: JSON payload to send.
            secret: Optional webhook secret for X-Webhook-Secret header.

        Returns:
            EventResponse with ok status and event_id.
        """
        headers: Optional[Dict[str, str]] = None
        if secret:
            headers = {"X-Webhook-Secret": secret}

        data = self._t.request(
            "POST",
            f"/events/{webhook_id}",
            json_body=payload or {},
            headers=headers,
        )
        return EventResponse.from_dict(data)


# ---------------------------------------------------------------------------
# Events (async)
# ---------------------------------------------------------------------------


class AsyncEvents:
    """Asynchronous event/webhook operations."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def send(
        self,
        *,
        webhook_id: str,
        payload: Optional[Dict[str, Any]] = None,
        secret: Optional[str] = None,
    ) -> EventResponse:
        """Send an event via webhook.

        Args:
            webhook_id: The webhook ID.
            payload: JSON payload to send.
            secret: Optional webhook secret for X-Webhook-Secret header.

        Returns:
            EventResponse with ok status and event_id.
        """
        headers: Optional[Dict[str, str]] = None
        if secret:
            headers = {"X-Webhook-Secret": secret}

        data = await self._t.request(
            "POST",
            f"/events/{webhook_id}",
            json_body=payload or {},
            headers=headers,
        )
        return EventResponse.from_dict(data)


# ---------------------------------------------------------------------------
# Billing (sync)
# ---------------------------------------------------------------------------


class Billing:
    """Synchronous billing and cost tracking operations."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def get_balance(self) -> UserBalance:
        """Get the authenticated user's current balance.

        Returns:
            UserBalance with balance in microdollars and USD.
        """
        data = self._t.request("GET", "/billing/balance")
        return UserBalance.from_dict(data)

    def get_transaction_history(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        types: Optional[str] = None,
        statuses: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None,
    ) -> TransactionHistoryResponse:
        """Get paginated, filterable transaction history.

        Args:
            page: Page number (1-based, default 1).
            limit: Items per page (max 100, default 20).
            types: Comma-separated filter: "credit", "debit", "refund".
            statuses: Comma-separated filter: "pending", "completed", "failed".
            start_date: Start date filter (YYYY-MM-DD).
            end_date: End date filter (YYYY-MM-DD).
            min_amount: Minimum amount in dollars.
            max_amount: Maximum amount in dollars.
            search: Search in description/metadata.

        Returns:
            TransactionHistoryResponse with transactions and pagination.
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if types is not None:
            params["types"] = types
        if statuses is not None:
            params["statuses"] = statuses
        if start_date is not None:
            params["start_date"] = start_date
        if end_date is not None:
            params["end_date"] = end_date
        if min_amount is not None:
            params["min_amount"] = min_amount
        if max_amount is not None:
            params["max_amount"] = max_amount
        if search is not None:
            params["search"] = search

        data = self._t.request("GET", "/billing/transactions", params=params)
        return TransactionHistoryResponse.from_dict(data)

    def get_activity_stats(self) -> ActivityStats:
        """Get aggregate activity statistics.

        Returns:
            ActivityStats with balance, total requests, spending,
            average cost per request, and token counts.
        """
        data = self._t.request("GET", "/activity/stats")
        return ActivityStats.from_dict(data)

    def get_daily_activity(self, *, days: int = 30) -> DailyActivityResponse:
        """Get daily aggregated spending and usage data.

        Args:
            days: Number of days to look back (default 30).

        Returns:
            DailyActivityResponse with daily data points.
        """
        params: Dict[str, Any] = {"days": days}
        data = self._t.request("GET", "/activity/daily", params=params)
        return DailyActivityResponse.from_dict(data)


# ---------------------------------------------------------------------------
# Billing (async)
# ---------------------------------------------------------------------------


class AsyncBilling:
    """Asynchronous billing and cost tracking operations."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def get_balance(self) -> UserBalance:
        """Get the authenticated user's current balance.

        Returns:
            UserBalance with balance in microdollars and USD.
        """
        data = await self._t.request("GET", "/billing/balance")
        return UserBalance.from_dict(data)

    async def get_transaction_history(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        types: Optional[str] = None,
        statuses: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None,
    ) -> TransactionHistoryResponse:
        """Get paginated, filterable transaction history.

        Args:
            page: Page number (1-based, default 1).
            limit: Items per page (max 100, default 20).
            types: Comma-separated filter: "credit", "debit", "refund".
            statuses: Comma-separated filter: "pending", "completed", "failed".
            start_date: Start date filter (YYYY-MM-DD).
            end_date: End date filter (YYYY-MM-DD).
            min_amount: Minimum amount in dollars.
            max_amount: Maximum amount in dollars.
            search: Search in description/metadata.

        Returns:
            TransactionHistoryResponse with transactions and pagination.
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if types is not None:
            params["types"] = types
        if statuses is not None:
            params["statuses"] = statuses
        if start_date is not None:
            params["start_date"] = start_date
        if end_date is not None:
            params["end_date"] = end_date
        if min_amount is not None:
            params["min_amount"] = min_amount
        if max_amount is not None:
            params["max_amount"] = max_amount
        if search is not None:
            params["search"] = search

        data = await self._t.request("GET", "/billing/transactions", params=params)
        return TransactionHistoryResponse.from_dict(data)

    async def get_activity_stats(self) -> ActivityStats:
        """Get aggregate activity statistics.

        Returns:
            ActivityStats with balance, total requests, spending,
            average cost per request, and token counts.
        """
        data = await self._t.request("GET", "/activity/stats")
        return ActivityStats.from_dict(data)

    async def get_daily_activity(self, *, days: int = 30) -> DailyActivityResponse:
        """Get daily aggregated spending and usage data.

        Args:
            days: Number of days to look back (default 30).

        Returns:
            DailyActivityResponse with daily data points.
        """
        params: Dict[str, Any] = {"days": days}
        data = await self._t.request("GET", "/activity/daily", params=params)
        return DailyActivityResponse.from_dict(data)


# ---------------------------------------------------------------------------
# Memory (sync)
# ---------------------------------------------------------------------------


class Memory:
    """Synchronous context memory operations."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(
        self,
        workflow_version_id: str,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> MemoryListResponse:
        """List memory instances for a workflow version.

        Args:
            workflow_version_id: The workflow version ID.
            limit: Instances per page (1-100, default 20).
            cursor: Pagination cursor from previous response.

        Returns:
            MemoryListResponse with instances and pagination info.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = self._t.request("GET", f"/chat-memories/{workflow_version_id}", params=params)
        return MemoryListResponse.from_dict(data)

    def get(
        self,
        agent_node_id: str,
        *,
        chat_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> MemoryGetResponse:
        """Get paginated memory messages for an agent node.

        Args:
            agent_node_id: The agent node ID.
            chat_id: The context memory ID (resolved chat/session ID).
            limit: Messages per page (1-100, default 20).
            cursor: Pagination cursor from previous response.

        Returns:
            MemoryGetResponse with messages and pagination info.
        """
        params: Dict[str, Any] = {"chat_id": chat_id, "limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = self._t.request("GET", f"/chat-memory/{agent_node_id}", params=params)
        return MemoryGetResponse.from_dict(data)

    def summarize(
        self,
        agent_node_id: str,
        *,
        context_memory_id: str,
        workflow_version_id: str,
        keep_last_n: Optional[int] = None,
        summarize_prompt: Optional[str] = None,
    ) -> MemoryActionResponse:
        """Summarize memory messages, replacing older messages with a summary.

        Args:
            agent_node_id: The agent node ID.
            context_memory_id: The context memory ID (resolved chat/session ID).
            workflow_version_id: The workflow version ID.
            keep_last_n: Number of recent messages to keep (rest are summarized).
            summarize_prompt: Custom summarization prompt (uses agent config default if omitted).

        Returns:
            MemoryActionResponse with the summary and deletion count.
        """
        body: Dict[str, Any] = {
            "action": "summarize",
            "context_memory_id": context_memory_id,
            "workflow_version_id": workflow_version_id,
        }
        if keep_last_n is not None:
            body["keep_last_n"] = keep_last_n
        if summarize_prompt is not None:
            body["summarize_prompt"] = summarize_prompt

        data = self._t.request("POST", f"/chat-memory/{agent_node_id}/actions", json_body=body)
        return MemoryActionResponse.from_dict(data)

    def trim(
        self,
        agent_node_id: str,
        *,
        context_memory_id: str,
        workflow_version_id: str,
        max_messages: Optional[int] = None,
    ) -> MemoryActionResponse:
        """Trim memory to a maximum number of messages (drop oldest).

        Args:
            agent_node_id: The agent node ID.
            context_memory_id: The context memory ID.
            workflow_version_id: The workflow version ID.
            max_messages: Maximum messages to keep (default 10).

        Returns:
            MemoryActionResponse with deletion count.
        """
        body: Dict[str, Any] = {
            "action": "trim",
            "context_memory_id": context_memory_id,
            "workflow_version_id": workflow_version_id,
        }
        if max_messages is not None:
            body["max_messages"] = max_messages

        data = self._t.request("POST", f"/chat-memory/{agent_node_id}/actions", json_body=body)
        return MemoryActionResponse.from_dict(data)

    def clear(
        self,
        agent_node_id: str,
        *,
        context_memory_id: str,
        workflow_version_id: str,
    ) -> MemoryActionResponse:
        """Clear all memory messages for a memory instance.

        Args:
            agent_node_id: The agent node ID.
            context_memory_id: The context memory ID.
            workflow_version_id: The workflow version ID.

        Returns:
            MemoryActionResponse with deletion count.
        """
        body: Dict[str, Any] = {
            "action": "clear",
            "context_memory_id": context_memory_id,
            "workflow_version_id": workflow_version_id,
        }
        data = self._t.request("POST", f"/chat-memory/{agent_node_id}/actions", json_body=body)
        return MemoryActionResponse.from_dict(data)

    def export(
        self,
        agent_node_id: str,
        *,
        context_memory_id: str,
        workflow_version_id: str,
    ) -> MemoryActionResponse:
        """Export all memory messages for a memory instance.

        Args:
            agent_node_id: The agent node ID.
            context_memory_id: The context memory ID.
            workflow_version_id: The workflow version ID.

        Returns:
            MemoryActionResponse with the full list of messages.
        """
        body: Dict[str, Any] = {
            "action": "export",
            "context_memory_id": context_memory_id,
            "workflow_version_id": workflow_version_id,
        }
        data = self._t.request("POST", f"/chat-memory/{agent_node_id}/actions", json_body=body)
        return MemoryActionResponse.from_dict(data)

    def delete(
        self,
        context_memory_id: str,
        *,
        memory_node_id: str,
        workflow_version_id: str,
    ) -> None:
        """Delete all memory for a specific memory instance.

        Args:
            context_memory_id: The context memory ID (used as path param).
            memory_node_id: The agent/memory node ID.
            workflow_version_id: The workflow version ID.
        """
        self._t.request(
            "DELETE",
            f"/chat-memories/{context_memory_id}",
            json_body={
                "memory_node_id": memory_node_id,
                "workflow_version_id": workflow_version_id,
            },
        )


# ---------------------------------------------------------------------------
# Memory (async)
# ---------------------------------------------------------------------------


class AsyncMemory:
    """Asynchronous context memory operations."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(
        self,
        workflow_version_id: str,
        *,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> MemoryListResponse:
        """List memory instances for a workflow version.

        Args:
            workflow_version_id: The workflow version ID.
            limit: Instances per page (1-100, default 20).
            cursor: Pagination cursor from previous response.

        Returns:
            MemoryListResponse with instances and pagination info.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = await self._t.request("GET", f"/chat-memories/{workflow_version_id}", params=params)
        return MemoryListResponse.from_dict(data)

    async def get(
        self,
        agent_node_id: str,
        *,
        chat_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> MemoryGetResponse:
        """Get paginated memory messages for an agent node.

        Args:
            agent_node_id: The agent node ID.
            chat_id: The context memory ID (resolved chat/session ID).
            limit: Messages per page (1-100, default 20).
            cursor: Pagination cursor from previous response.

        Returns:
            MemoryGetResponse with messages and pagination info.
        """
        params: Dict[str, Any] = {"chat_id": chat_id, "limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        data = await self._t.request("GET", f"/chat-memory/{agent_node_id}", params=params)
        return MemoryGetResponse.from_dict(data)

    async def summarize(
        self,
        agent_node_id: str,
        *,
        context_memory_id: str,
        workflow_version_id: str,
        keep_last_n: Optional[int] = None,
        summarize_prompt: Optional[str] = None,
    ) -> MemoryActionResponse:
        """Summarize memory messages, replacing older messages with a summary.

        Args:
            agent_node_id: The agent node ID.
            context_memory_id: The context memory ID (resolved chat/session ID).
            workflow_version_id: The workflow version ID.
            keep_last_n: Number of recent messages to keep (rest are summarized).
            summarize_prompt: Custom summarization prompt (uses agent config default if omitted).

        Returns:
            MemoryActionResponse with the summary and deletion count.
        """
        body: Dict[str, Any] = {
            "action": "summarize",
            "context_memory_id": context_memory_id,
            "workflow_version_id": workflow_version_id,
        }
        if keep_last_n is not None:
            body["keep_last_n"] = keep_last_n
        if summarize_prompt is not None:
            body["summarize_prompt"] = summarize_prompt

        data = await self._t.request("POST", f"/chat-memory/{agent_node_id}/actions", json_body=body)
        return MemoryActionResponse.from_dict(data)

    async def trim(
        self,
        agent_node_id: str,
        *,
        context_memory_id: str,
        workflow_version_id: str,
        max_messages: Optional[int] = None,
    ) -> MemoryActionResponse:
        """Trim memory to a maximum number of messages (drop oldest).

        Args:
            agent_node_id: The agent node ID.
            context_memory_id: The context memory ID.
            workflow_version_id: The workflow version ID.
            max_messages: Maximum messages to keep (default 10).

        Returns:
            MemoryActionResponse with deletion count.
        """
        body: Dict[str, Any] = {
            "action": "trim",
            "context_memory_id": context_memory_id,
            "workflow_version_id": workflow_version_id,
        }
        if max_messages is not None:
            body["max_messages"] = max_messages

        data = await self._t.request("POST", f"/chat-memory/{agent_node_id}/actions", json_body=body)
        return MemoryActionResponse.from_dict(data)

    async def clear(
        self,
        agent_node_id: str,
        *,
        context_memory_id: str,
        workflow_version_id: str,
    ) -> MemoryActionResponse:
        """Clear all memory messages for a memory instance.

        Args:
            agent_node_id: The agent node ID.
            context_memory_id: The context memory ID.
            workflow_version_id: The workflow version ID.

        Returns:
            MemoryActionResponse with deletion count.
        """
        body: Dict[str, Any] = {
            "action": "clear",
            "context_memory_id": context_memory_id,
            "workflow_version_id": workflow_version_id,
        }
        data = await self._t.request("POST", f"/chat-memory/{agent_node_id}/actions", json_body=body)
        return MemoryActionResponse.from_dict(data)

    async def export(
        self,
        agent_node_id: str,
        *,
        context_memory_id: str,
        workflow_version_id: str,
    ) -> MemoryActionResponse:
        """Export all memory messages for a memory instance.

        Args:
            agent_node_id: The agent node ID.
            context_memory_id: The context memory ID.
            workflow_version_id: The workflow version ID.

        Returns:
            MemoryActionResponse with the full list of messages.
        """
        body: Dict[str, Any] = {
            "action": "export",
            "context_memory_id": context_memory_id,
            "workflow_version_id": workflow_version_id,
        }
        data = await self._t.request("POST", f"/chat-memory/{agent_node_id}/actions", json_body=body)
        return MemoryActionResponse.from_dict(data)

    async def delete(
        self,
        context_memory_id: str,
        *,
        memory_node_id: str,
        workflow_version_id: str,
    ) -> None:
        """Delete all memory for a specific memory instance.

        Args:
            context_memory_id: The context memory ID (used as path param).
            memory_node_id: The agent/memory node ID.
            workflow_version_id: The workflow version ID.
        """
        await self._t.request(
            "DELETE",
            f"/chat-memories/{context_memory_id}",
            json_body={
                "memory_node_id": memory_node_id,
                "workflow_version_id": workflow_version_id,
            },
        )


# ---------------------------------------------------------------------------
# LLM (sync)
# ---------------------------------------------------------------------------


class LLM:
    """Synchronous LLM inference via the Splox /chat/completions endpoint."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> ChatCompletion:
        """Send a chat completion request.

        Args:
            model: Model identifier (e.g. ``openai/gpt-4o``).
            messages: List of message dicts with ``role`` and ``content``.
            **kwargs: Additional OpenAI-compatible parameters (temperature, max_tokens, etc.).

        Returns:
            ChatCompletion with id, model, choices, and usage.
        """
        body: Dict[str, Any] = {"model": model, "messages": messages, **kwargs}
        data = self._t.request("POST", "/chat/completions", json_body=body)
        return ChatCompletion.from_dict(data)


# ---------------------------------------------------------------------------
# AsyncLLM
# ---------------------------------------------------------------------------


class AsyncLLM:
    """Asynchronous LLM inference via the Splox /chat/completions endpoint."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> ChatCompletion:
        """Send a chat completion request.

        Args:
            model: Model identifier (e.g. ``openai/gpt-4o``).
            messages: List of message dicts with ``role`` and ``content``.
            **kwargs: Additional OpenAI-compatible parameters (temperature, max_tokens, etc.).

        Returns:
            ChatCompletion with id, model, choices, and usage.
        """
        body: Dict[str, Any] = {"model": model, "messages": messages, **kwargs}
        data = await self._t.request("POST", "/chat/completions", json_body=body)
        return ChatCompletion.from_dict(data)


def notify(webhook_url: str, data: Any) -> None:
    """POST data to a webhook URL as JSON.

    Args:
        webhook_url: The URL to POST to.
        data: Any JSON-serialisable payload.
    """
    import urllib.request, json as _json
    body = _json.dumps(data).encode()
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10):
        pass


async def async_notify(webhook_url: str, data: Any) -> None:
    """Async POST data to a webhook URL as JSON.

    Args:
        webhook_url: The URL to POST to.
        data: Any JSON-serialisable payload.
    """
    import json as _json
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            await session.post(webhook_url, json=data, timeout=aiohttp.ClientTimeout(total=10))
    except ImportError:
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, notify, webhook_url, data)
