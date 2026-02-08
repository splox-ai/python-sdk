"""Resource namespaces for the Splox API — Workflows, Chats, Events."""

from __future__ import annotations

import time
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

from splox._models import (
    Chat,
    ChatHistoryResponse,
    ChatListResponse,
    ChatMessage,
    EventResponse,
    ExecutionTreeResponse,
    HistoryResponse,
    RunResponse,
    SSEEvent,
    StartNodesResponse,
    WorkflowFull,
    WorkflowListResponse,
    WorkflowRequestFile,
    WorkflowVersion,
    WorkflowVersionListResponse,
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
    ) -> RunResponse:
        """Trigger a workflow execution.

        Args:
            workflow_version_id: ID of the workflow version to execute.
            chat_id: Chat session ID.
            start_node_id: ID of the Start node to begin execution at.
            query: The user message or query text.
            files: Optional file attachments.
            additional_params: Optional extra parameters.

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
    ) -> RunResponse:
        """Trigger a workflow execution.

        Args:
            workflow_version_id: ID of the workflow version to execute.
            chat_id: Chat session ID.
            start_node_id: ID of the Start node to begin execution at.
            query: The user message or query text.
            files: Optional file attachments.
            additional_params: Optional extra parameters.

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
