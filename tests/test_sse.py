"""Tests for SSE parsing."""

from splox._transport import _parse_sse_line


class TestSSEParsing:
    def test_keepalive(self) -> None:
        event = _parse_sse_line("data: keepalive")
        assert event is not None
        assert event.is_keepalive is True

    def test_json_data(self) -> None:
        line = 'data: {"workflow_request":{"id":"req-1","workflow_version_id":"v1","start_node_id":"n1","status":"completed","created_at":"2025-01-01T00:00:00Z"}}'
        event = _parse_sse_line(line)
        assert event is not None
        assert event.workflow_request is not None
        assert event.workflow_request.id == "req-1"
        assert event.workflow_request.status == "completed"

    def test_empty_line(self) -> None:
        assert _parse_sse_line("") is None
        assert _parse_sse_line("   ") is None

    def test_non_data_line(self) -> None:
        assert _parse_sse_line("event: update") is None
        assert _parse_sse_line(": comment") is None

    def test_invalid_json(self) -> None:
        event = _parse_sse_line("data: {invalid json}")
        assert event is not None
        assert event.raw_data == "{invalid json}"
        assert event.workflow_request is None

    def test_workflow_status_event(self) -> None:
        line = 'data: {"is_active":false,"type":"workflow_status"}'
        event = _parse_sse_line(line)
        assert event is not None
        assert event.workflow_request is None
        assert event.raw_data is None  # It parsed as valid JSON but no WR/NE

    def test_full_event_with_node_execution(self) -> None:
        data = {
            "workflow_request": {
                "id": "req-1",
                "workflow_version_id": "v1",
                "start_node_id": "n1",
                "status": "in_progress",
                "created_at": "2025-01-01T00:00:00Z",
            },
            "node_execution": {
                "id": "ne-1",
                "workflow_request_id": "req-1",
                "node_id": "n1",
                "workflow_version_id": "v1",
                "status": "completed",
                "output_data": {"text": "Hello world"},
            },
        }
        import json

        event = _parse_sse_line(f"data: {json.dumps(data)}")
        assert event is not None
        assert event.workflow_request is not None
        assert event.node_execution is not None
        assert event.node_execution.output_data == {"text": "Hello world"}
