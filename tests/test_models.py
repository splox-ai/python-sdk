"""Tests for Splox data models."""

from splox._models import (
    Chat,
    ChildExecution,
    EventResponse,
    ExecutionNode,
    ExecutionTree,
    ExecutionTreeResponse,
    HistoryResponse,
    NodeExecution,
    Pagination,
    RunResponse,
    SSEEvent,
    WorkflowRequest,
    WorkflowRequestFile,
)


class TestWorkflowRequestFile:
    def test_to_dict_minimal(self) -> None:
        f = WorkflowRequestFile(url="https://example.com/file.pdf")
        assert f.to_dict() == {"url": "https://example.com/file.pdf"}

    def test_to_dict_full(self) -> None:
        f = WorkflowRequestFile(
            url="https://example.com/file.pdf",
            content_type="application/pdf",
            file_name="report.pdf",
            file_size=1024,
            metadata={"key": "value"},
        )
        d = f.to_dict()
        assert d["url"] == "https://example.com/file.pdf"
        assert d["content_type"] == "application/pdf"
        assert d["file_name"] == "report.pdf"
        assert d["file_size"] == 1024
        assert d["metadata"] == {"key": "value"}


class TestWorkflowRequest:
    def test_from_dict_minimal(self) -> None:
        data = {
            "id": "req-1",
            "workflow_version_id": "ver-1",
            "start_node_id": "node-1",
            "status": "pending",
            "created_at": "2025-01-01T00:00:00Z",
        }
        wr = WorkflowRequest.from_dict(data)
        assert wr.id == "req-1"
        assert wr.status == "pending"
        assert wr.chat_id is None

    def test_from_dict_full(self) -> None:
        data = {
            "id": "req-1",
            "workflow_version_id": "ver-1",
            "start_node_id": "node-1",
            "status": "completed",
            "created_at": "2025-01-01T00:00:00Z",
            "user_id": "user-1",
            "chat_id": "chat-1",
            "payload": {"text": "hello"},
            "started_at": "2025-01-01T00:00:01Z",
            "completed_at": "2025-01-01T00:00:10Z",
        }
        wr = WorkflowRequest.from_dict(data)
        assert wr.status == "completed"
        assert wr.chat_id == "chat-1"
        assert wr.payload == {"text": "hello"}


class TestNodeExecution:
    def test_from_dict(self) -> None:
        data = {
            "id": "ne-1",
            "workflow_request_id": "req-1",
            "node_id": "node-1",
            "workflow_version_id": "ver-1",
            "status": "completed",
            "output_data": {"result": "ok"},
            "attempt_count": 1,
        }
        ne = NodeExecution.from_dict(data)
        assert ne.status == "completed"
        assert ne.output_data == {"result": "ok"}


class TestExecutionTree:
    def test_from_dict_with_children(self) -> None:
        data = {
            "workflow_request_id": "req-1",
            "status": "completed",
            "created_at": "2025-01-01T00:00:00Z",
            "completed_at": "2025-01-01T00:01:00Z",
            "nodes": [
                {
                    "id": "en-1",
                    "node_id": "node-1",
                    "status": "completed",
                    "node_label": "Start",
                    "node_type": "start",
                    "child_executions": [
                        {
                            "index": 0,
                            "workflow_request_id": "req-2",
                            "status": "completed",
                            "label": "Agent B",
                            "nodes": [],
                        }
                    ],
                    "total_children": 1,
                    "has_more_children": False,
                }
            ],
        }
        tree = ExecutionTree.from_dict(data)
        assert tree.status == "completed"
        assert len(tree.nodes) == 1
        assert tree.nodes[0].node_label == "Start"
        assert len(tree.nodes[0].child_executions) == 1
        assert tree.nodes[0].child_executions[0].label == "Agent B"


class TestChat:
    def test_from_dict(self) -> None:
        data = {
            "id": "chat-1",
            "name": "Test Chat",
            "user_id": "user-1",
            "resource_type": "api",
            "resource_id": "wf-1",
            "is_public": False,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }
        chat = Chat.from_dict(data)
        assert chat.id == "chat-1"
        assert chat.name == "Test Chat"
        assert chat.is_public is False


class TestRunResponse:
    def test_from_dict(self) -> None:
        r = RunResponse.from_dict({"workflow_request_id": "req-123"})
        assert r.workflow_request_id == "req-123"


class TestExecutionTreeResponse:
    def test_from_dict(self) -> None:
        data = {
            "execution_tree": {
                "workflow_request_id": "req-1",
                "status": "completed",
                "created_at": "2025-01-01T00:00:00Z",
                "nodes": [],
            }
        }
        resp = ExecutionTreeResponse.from_dict(data)
        assert resp.execution_tree.status == "completed"


class TestHistoryResponse:
    def test_from_dict(self) -> None:
        data = {
            "data": [
                {
                    "id": "req-1",
                    "workflow_version_id": "ver-1",
                    "start_node_id": "node-1",
                    "status": "completed",
                    "created_at": "2025-01-01T00:00:00Z",
                }
            ],
            "pagination": {"limit": 10, "next_cursor": "req-0"},
        }
        resp = HistoryResponse.from_dict(data)
        assert len(resp.data) == 1
        assert resp.pagination.next_cursor == "req-0"


class TestEventResponse:
    def test_from_dict(self) -> None:
        r = EventResponse.from_dict({"ok": True, "event_id": "evt-1"})
        assert r.ok is True
        assert r.event_id == "evt-1"


class TestSSEEvent:
    def test_keepalive(self) -> None:
        e = SSEEvent(is_keepalive=True, raw_data="keepalive")
        assert e.is_keepalive is True
        assert e.workflow_request is None

    def test_from_dict_with_data(self) -> None:
        data = {
            "workflow_request": {
                "id": "req-1",
                "workflow_version_id": "ver-1",
                "start_node_id": "node-1",
                "status": "in_progress",
                "created_at": "2025-01-01T00:00:00Z",
            },
            "node_execution": {
                "id": "ne-1",
                "workflow_request_id": "req-1",
                "node_id": "node-1",
                "workflow_version_id": "ver-1",
                "status": "completed",
            },
        }
        e = SSEEvent.from_dict(data)
        assert e.workflow_request is not None
        assert e.workflow_request.status == "in_progress"
        assert e.node_execution is not None
        assert e.node_execution.status == "completed"
