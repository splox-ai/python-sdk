"""Tests for the Splox client and transport layer."""

import json

import httpx
import pytest

from splox import AsyncSploxClient, SploxClient
from splox.exceptions import (
    SploxAPIError,
    SploxAuthError,
    SploxForbiddenError,
    SploxGoneError,
    SploxNotFoundError,
    SploxRateLimitError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_chat_response() -> dict:
    return {
        "id": "chat-001",
        "name": "Test Chat",
        "user_id": "user-001",
        "resource_type": "api",
        "resource_id": "wf-001",
        "is_public": False,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_run_response() -> dict:
    return {"workflow_request_id": "req-001"}


@pytest.fixture
def mock_execution_tree_response() -> dict:
    return {
        "execution_tree": {
            "workflow_request_id": "req-001",
            "status": "completed",
            "created_at": "2025-01-01T00:00:00Z",
            "completed_at": "2025-01-01T00:01:00Z",
            "nodes": [
                {
                    "id": "en-001",
                    "node_id": "node-001",
                    "status": "completed",
                    "node_label": "Start",
                    "node_type": "start",
                    "input_data": {},
                    "output_data": {"text": "result"},
                    "child_executions": [],
                    "total_children": 0,
                    "has_more_children": False,
                }
            ],
        }
    }


@pytest.fixture
def mock_history_response() -> dict:
    return {
        "data": [
            {
                "id": "req-001",
                "workflow_version_id": "ver-001",
                "start_node_id": "node-001",
                "status": "completed",
                "created_at": "2025-01-01T00:00:00Z",
            }
        ],
        "pagination": {"limit": 10, "next_cursor": None},
    }


@pytest.fixture
def mock_event_response() -> dict:
    return {"ok": True, "event_id": "evt-001"}


@pytest.fixture
def mock_mcp_user_servers_response() -> dict:
    return {
        "servers": [
            {
                "id": "0199e001-a23b-7c8d-1234-567890abcdef",
                "user_id": "user-001",
                "name": "Docs MCP",
                "url": "https://mcp.example.com",
                "transport_type": "streamable_http",
                "auth_type": "manual",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "status": "active",
                "has_credential": True,
            }
        ],
        "total": 1,
    }


@pytest.fixture
def mock_mcp_server_tools_response() -> dict:
    return {
        "options": [
            {
                "label": "List Servers",
                "value": "list_servers",
            },
            {
                "label": "Get Server",
                "value": "get_server",
            },
        ],
        "total": 2,
        "limit": 2,
    }


# ---------------------------------------------------------------------------
# Sync client tests
# ---------------------------------------------------------------------------


class TestSyncClient:
    def test_create_chat(self, httpx_mock, mock_chat_response) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/chats",
            json=mock_chat_response,
            status_code=201,
        )

        client = SploxClient(api_key="test-key")
        chat = client.chats.create(name="Test Chat", resource_id="wf-001")

        assert chat.id == "chat-001"
        assert chat.name == "Test Chat"
        assert chat.resource_type == "api"
        client.close()

    def test_get_chat(self, httpx_mock, mock_chat_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/chats/chat-001",
            json=mock_chat_response,
        )

        client = SploxClient(api_key="test-key")
        chat = client.chats.get("chat-001")
        assert chat.id == "chat-001"
        client.close()

    def test_run_workflow(self, httpx_mock, mock_run_response) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/workflow-requests/run",
            json=mock_run_response,
        )

        client = SploxClient(api_key="test-key")
        result = client.workflows.run(
            workflow_version_id="ver-001",
            chat_id="chat-001",
            start_node_id="node-001",
            query="Hello",
        )
        assert result.workflow_request_id == "req-001"

        # Verify the request body
        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert body["query"] == "Hello"
        assert body["workflow_version_id"] == "ver-001"
        client.close()

    def test_run_workflow_with_files(self, httpx_mock, mock_run_response) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/workflow-requests/run",
            json=mock_run_response,
        )

        from splox import WorkflowRequestFile

        client = SploxClient(api_key="test-key")
        result = client.workflows.run(
            workflow_version_id="ver-001",
            chat_id="chat-001",
            start_node_id="node-001",
            query="Analyze this file",
            files=[
                WorkflowRequestFile(
                    url="https://example.com/file.pdf",
                    content_type="application/pdf",
                    file_name="report.pdf",
                )
            ],
        )
        assert result.workflow_request_id == "req-001"

        request = httpx_mock.get_request()
        body = json.loads(request.content)
        assert len(body["files"]) == 1
        assert body["files"][0]["url"] == "https://example.com/file.pdf"
        client.close()

    def test_get_execution_tree(self, httpx_mock, mock_execution_tree_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/workflow-requests/req-001/execution-tree",
            json=mock_execution_tree_response,
        )

        client = SploxClient(api_key="test-key")
        resp = client.workflows.get_execution_tree("req-001")
        assert resp.execution_tree.status == "completed"
        assert len(resp.execution_tree.nodes) == 1
        assert resp.execution_tree.nodes[0].node_label == "Start"
        client.close()

    def test_get_history(self, httpx_mock, mock_history_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url=httpx.URL(
                "https://app.splox.io/api/v1/workflow-requests/req-001/history",
                params={"limit": "10"},
            ),
            json=mock_history_response,
        )

        client = SploxClient(api_key="test-key")
        resp = client.workflows.get_history("req-001")
        assert len(resp.data) == 1
        assert resp.pagination.next_cursor is None
        client.close()

    def test_stop_workflow(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/workflow-requests/req-001/stop",
            status_code=200,
        )

        client = SploxClient(api_key="test-key")
        client.workflows.stop("req-001")  # Should not raise
        client.close()

    def test_send_event(self, httpx_mock, mock_event_response) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/events/wh-001",
            json=mock_event_response,
        )

        client = SploxClient(api_key="test-key")
        resp = client.events.send(
            webhook_id="wh-001",
            payload={"order": "12345"},
        )
        assert resp.ok is True
        assert resp.event_id == "evt-001"
        client.close()

    def test_send_event_with_secret(self, httpx_mock, mock_event_response) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/events/wh-001",
            json=mock_event_response,
        )

        client = SploxClient(api_key="test-key")
        client.events.send(
            webhook_id="wh-001",
            payload={"order": "12345"},
            secret="my-secret",
        )

        request = httpx_mock.get_request()
        assert request.headers["X-Webhook-Secret"] == "my-secret"
        client.close()

    def test_context_manager(self, httpx_mock, mock_chat_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/chats/chat-001",
            json=mock_chat_response,
        )

        with SploxClient(api_key="test-key") as client:
            chat = client.chats.get("chat-001")
            assert chat.id == "chat-001"

    def test_custom_base_url(self, httpx_mock, mock_chat_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://custom.example.com/api/v1/chats/chat-001",
            json=mock_chat_response,
        )

        client = SploxClient(
            api_key="test-key",
            base_url="https://custom.example.com/api/v1",
        )
        chat = client.chats.get("chat-001")
        assert chat.id == "chat-001"
        client.close()

    def test_mcp_list_user_servers(self, httpx_mock, mock_mcp_user_servers_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/user-mcp-servers",
            json=mock_mcp_user_servers_response,
        )

        client = SploxClient(api_key="test-key")
        resp = client.mcp.list_user_servers()

        assert resp.total == 1
        assert len(resp.servers) == 1
        assert resp.servers[0].url == "https://mcp.example.com"
        assert resp.servers[0].id == "0199e001-a23b-7c8d-1234-567890abcdef"
        client.close()

    def test_mcp_get_server_tools(self, httpx_mock, mock_mcp_server_tools_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/user-mcp-servers/0199e001-a23b-7c8d-1234-567890abcdef/tools",
            json=mock_mcp_server_tools_response,
        )

        client = SploxClient(api_key="test-key")
        resp = client.mcp.get_server_tools("0199e001-a23b-7c8d-1234-567890abcdef")

        assert resp.total == 2
        assert resp.limit == 2
        assert len(resp.options) == 2
        assert resp.options[0].value == "list_servers"
        client.close()


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_401_raises_auth_error(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/chats/chat-001",
            json={"error": "Invalid token"},
            status_code=401,
        )

        client = SploxClient(api_key="bad-key")
        with pytest.raises(SploxAuthError) as exc_info:
            client.chats.get("chat-001")
        assert exc_info.value.status_code == 401
        client.close()

    def test_403_raises_forbidden_error(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/chats/chat-001",
            json={"error": "Webhook disabled"},
            status_code=403,
        )

        client = SploxClient(api_key="test-key")
        with pytest.raises(SploxForbiddenError):
            client.chats.get("chat-001")
        client.close()

    def test_404_raises_not_found_error(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/chats/missing",
            status_code=404,
        )

        client = SploxClient(api_key="test-key")
        with pytest.raises(SploxNotFoundError):
            client.chats.get("missing")
        client.close()

    def test_410_raises_gone_error(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/events/wh-expired",
            json={"error": "Webhook expired"},
            status_code=410,
        )

        client = SploxClient(api_key="test-key")
        with pytest.raises(SploxGoneError):
            client.events.send(webhook_id="wh-expired")
        client.close()

    def test_429_raises_rate_limit_error(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/workflow-requests/run",
            json={"error": "Rate limit exceeded"},
            status_code=429,
            headers={"Retry-After": "60"},
        )

        client = SploxClient(api_key="test-key")
        with pytest.raises(SploxRateLimitError) as exc_info:
            client.workflows.run(
                workflow_version_id="ver-001",
                chat_id="chat-001",
                start_node_id="node-001",
                query="test",
            )
        assert exc_info.value.retry_after == 60.0
        client.close()

    def test_500_raises_api_error(self, httpx_mock) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/chats/chat-001",
            json={"error": "Internal server error"},
            status_code=500,
        )

        client = SploxClient(api_key="test-key")
        with pytest.raises(SploxAPIError) as exc_info:
            client.chats.get("chat-001")
        assert exc_info.value.status_code == 500
        client.close()


# ---------------------------------------------------------------------------
# Async client tests
# ---------------------------------------------------------------------------


class TestAsyncClient:
    @pytest.mark.asyncio
    async def test_create_chat(self, httpx_mock, mock_chat_response) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/chats",
            json=mock_chat_response,
            status_code=201,
        )

        async with AsyncSploxClient(api_key="test-key") as client:
            chat = await client.chats.create(name="Test Chat", resource_id="wf-001")
            assert chat.id == "chat-001"

    @pytest.mark.asyncio
    async def test_run_workflow(self, httpx_mock, mock_run_response) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/workflow-requests/run",
            json=mock_run_response,
        )

        async with AsyncSploxClient(api_key="test-key") as client:
            result = await client.workflows.run(
                workflow_version_id="ver-001",
                chat_id="chat-001",
                start_node_id="node-001",
                query="Hello",
            )
            assert result.workflow_request_id == "req-001"

    @pytest.mark.asyncio
    async def test_get_execution_tree(self, httpx_mock, mock_execution_tree_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/workflow-requests/req-001/execution-tree",
            json=mock_execution_tree_response,
        )

        async with AsyncSploxClient(api_key="test-key") as client:
            resp = await client.workflows.get_execution_tree("req-001")
            assert resp.execution_tree.status == "completed"

    @pytest.mark.asyncio
    async def test_send_event(self, httpx_mock, mock_event_response) -> None:
        httpx_mock.add_response(
            method="POST",
            url="https://app.splox.io/api/v1/events/wh-001",
            json=mock_event_response,
        )

        async with AsyncSploxClient(api_key="test-key") as client:
            resp = await client.events.send(
                webhook_id="wh-001",
                payload={"order": "12345"},
            )
            assert resp.ok is True

    @pytest.mark.asyncio
    async def test_mcp_list_user_servers(self, httpx_mock, mock_mcp_user_servers_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/user-mcp-servers",
            json=mock_mcp_user_servers_response,
        )

        async with AsyncSploxClient(api_key="test-key") as client:
            resp = await client.mcp.list_user_servers()
            assert resp.total == 1
            assert len(resp.servers) == 1
            assert resp.servers[0].name == "Docs MCP"

    @pytest.mark.asyncio
    async def test_mcp_get_server_tools(self, httpx_mock, mock_mcp_server_tools_response) -> None:
        httpx_mock.add_response(
            method="GET",
            url="https://app.splox.io/api/v1/user-mcp-servers/0199e001-a23b-7c8d-1234-567890abcdef/tools",
            json=mock_mcp_server_tools_response,
        )

        async with AsyncSploxClient(api_key="test-key") as client:
            resp = await client.mcp.get_server_tools("0199e001-a23b-7c8d-1234-567890abcdef")
            assert resp.total == 2
            assert resp.options[0].value == "list_servers"
