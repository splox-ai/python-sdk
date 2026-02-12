"""Pydantic-free data models for the Splox API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowRequestFile:
    """File attached to a workflow request."""

    url: str
    content_type: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"url": self.url}
        if self.content_type is not None:
            d["content_type"] = self.content_type
        if self.file_name is not None:
            d["file_name"] = self.file_name
        if self.file_size is not None:
            d["file_size"] = self.file_size
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d


@dataclass
class WorkflowRequest:
    """Represents a workflow execution request."""

    id: str
    workflow_version_id: str
    start_node_id: str
    status: str
    created_at: str
    user_id: Optional[str] = None
    billing_user_id: Optional[str] = None
    parent_node_execution_id: Optional[str] = None
    parent_workflow_request_id: Optional[str] = None
    chat_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowRequest:
        return cls(
            id=data["id"],
            workflow_version_id=data["workflow_version_id"],
            start_node_id=data["start_node_id"],
            status=data["status"],
            created_at=data["created_at"],
            user_id=data.get("user_id"),
            billing_user_id=data.get("billing_user_id"),
            parent_node_execution_id=data.get("parent_node_execution_id"),
            parent_workflow_request_id=data.get("parent_workflow_request_id"),
            chat_id=data.get("chat_id"),
            payload=data.get("payload"),
            metadata=data.get("metadata"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class NodeExecution:
    """Represents the execution state of a single node."""

    id: str
    workflow_request_id: str
    node_id: str
    workflow_version_id: str
    status: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    attempt_count: Optional[int] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NodeExecution:
        return cls(
            id=data["id"],
            workflow_request_id=data["workflow_request_id"],
            node_id=data["node_id"],
            workflow_version_id=data["workflow_version_id"],
            status=data["status"],
            input_data=data.get("input_data"),
            output_data=data.get("output_data"),
            attempt_count=data.get("attempt_count"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            failed_at=data.get("failed_at"),
        )


@dataclass
class ChildExecution:
    """Represents a child agent execution within a node."""

    index: int
    workflow_request_id: str
    status: str
    label: Optional[str] = None
    target_node_label: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    nodes: List[ExecutionNode] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChildExecution:
        return cls(
            index=data["index"],
            workflow_request_id=data["workflow_request_id"],
            status=data["status"],
            label=data.get("label"),
            target_node_label=data.get("target_node_label"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            nodes=[ExecutionNode.from_dict(n) for n in data.get("nodes", [])],
        )


@dataclass
class ExecutionNode:
    """Represents a node in the execution tree."""

    id: str
    node_id: str
    status: str
    node_label: Optional[str] = None
    node_type: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    failed_at: Optional[str] = None
    attempt_count: Optional[int] = None
    child_executions: List[ChildExecution] = field(default_factory=list)
    total_children: Optional[int] = None
    has_more_children: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionNode:
        return cls(
            id=data["id"],
            node_id=data["node_id"],
            status=data["status"],
            node_label=data.get("node_label"),
            node_type=data.get("node_type"),
            input_data=data.get("input_data"),
            output_data=data.get("output_data"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
            failed_at=data.get("failed_at"),
            attempt_count=data.get("attempt_count"),
            child_executions=[
                ChildExecution.from_dict(c) for c in data.get("child_executions", [])
            ],
            total_children=data.get("total_children"),
            has_more_children=data.get("has_more_children"),
        )


@dataclass
class ExecutionTree:
    """Complete execution tree for a workflow run."""

    workflow_request_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    nodes: List[ExecutionNode] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionTree:
        return cls(
            workflow_request_id=data["workflow_request_id"],
            status=data["status"],
            created_at=data["created_at"],
            completed_at=data.get("completed_at"),
            nodes=[ExecutionNode.from_dict(n) for n in data.get("nodes", [])],
        )


@dataclass
class Chat:
    """Represents a chat session."""

    id: str
    name: str
    user_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    is_public: Optional[bool] = None
    public_share_token: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Chat:
        return cls(
            id=data["id"],
            name=data["name"],
            user_id=data.get("user_id"),
            resource_type=data.get("resource_type"),
            resource_id=data.get("resource_id"),
            is_public=data.get("is_public"),
            public_share_token=data.get("public_share_token"),
            metadata=data.get("metadata"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class ChatMessageContent:
    """A single content block within a chat message."""

    type: str
    text: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    reasoning: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChatMessageContent:
        return cls(
            type=data.get("type", ""),
            text=data.get("text"),
            tool_call_id=data.get("toolCallId"),
            tool_name=data.get("toolName"),
            args=data.get("args"),
            result=data.get("result"),
            reasoning=data.get("reasoning"),
        )


@dataclass
class ChatMessage:
    """A single message in a chat history."""

    id: str
    chat_id: str
    role: str
    content: List[ChatMessageContent] = field(default_factory=list)
    parent_id: Optional[str] = None
    status: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    files: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChatMessage:
        content = [ChatMessageContent.from_dict(c) for c in (data.get("content") or [])]
        return cls(
            id=data["id"],
            chat_id=data["chat_id"],
            role=data["role"],
            content=content,
            parent_id=data.get("parent_id"),
            status=data.get("status"),
            metadata=data.get("metadata"),
            files=data.get("files"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class Pagination:
    """Cursor-based pagination info."""

    limit: int
    next_cursor: Optional[str] = None
    has_more: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Pagination:
        return cls(
            limit=data["limit"],
            next_cursor=data.get("next_cursor"),
            has_more=data.get("has_more", False),
        )


# --- Workflow / Version / Node / Edge models ---


@dataclass
class WorkflowVersion:
    """Represents a specific version of a workflow."""

    id: str
    workflow_id: str
    version_number: int
    name: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowVersion:
        return cls(
            id=data["id"],
            workflow_id=data["workflow_id"],
            version_number=data["version_number"],
            name=data["name"],
            status=data["status"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            description=data.get("description"),
            metadata=data.get("metadata"),
        )


@dataclass
class Workflow:
    """Represents a workflow."""

    id: str
    user_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    latest_version: Optional[WorkflowVersion] = None
    is_public: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Workflow:
        lv = None
        if data.get("latest_version"):
            lv = WorkflowVersion.from_dict(data["latest_version"])
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            latest_version=lv,
            is_public=data.get("is_public"),
        )


@dataclass
class Node:
    """Represents a node in a workflow."""

    id: str
    workflow_version_id: str
    node_type: str
    label: str
    pos_x: Optional[float] = None
    pos_y: Optional[float] = None
    parent_id: Optional[str] = None
    extent: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Node:
        return cls(
            id=data["id"],
            workflow_version_id=data["workflow_version_id"],
            node_type=data["node_type"],
            label=data["label"],
            pos_x=data.get("pos_x"),
            pos_y=data.get("pos_y"),
            parent_id=data.get("parent_id"),
            extent=data.get("extent"),
            data=data.get("data"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class Edge:
    """Represents an edge (connection) between nodes."""

    id: str
    workflow_version_id: str
    source: str
    target: str
    edge_type: str
    source_handle: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Edge:
        return cls(
            id=data["id"],
            workflow_version_id=data["workflow_version_id"],
            source=data["source"],
            target=data["target"],
            edge_type=data["edge_type"],
            source_handle=data.get("source_handle"),
            data=data.get("data"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class WorkflowFull:
    """Full workflow with version, nodes, and edges."""

    workflow: Workflow
    workflow_version: WorkflowVersion
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowFull:
        return cls(
            workflow=Workflow.from_dict(data["workflow"]),
            workflow_version=WorkflowVersion.from_dict(data["workflow_version"]),
            nodes=[Node.from_dict(n) for n in (data.get("nodes") or [])],
            edges=[Edge.from_dict(e) for e in (data.get("edges") or [])],
        )


# --- Response wrappers ---


@dataclass
class WorkflowListResponse:
    """Response from listing workflows."""

    workflows: List[Workflow]
    pagination: Pagination

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowListResponse:
        return cls(
            workflows=[Workflow.from_dict(w) for w in (data.get("workflows") or [])],
            pagination=Pagination.from_dict(data["pagination"]),
        )


@dataclass
class StartNodesResponse:
    """Response from getting start nodes."""

    nodes: List[Node]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StartNodesResponse:
        return cls(
            nodes=[Node.from_dict(n) for n in (data.get("nodes") or [])],
        )


@dataclass
class ChatListResponse:
    """Response from listing chats for a resource."""

    chats: List[Chat]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChatListResponse:
        return cls(
            chats=[Chat.from_dict(c) for c in (data.get("chats") or [])],
        )


@dataclass
class WorkflowVersionListResponse:
    """Response from listing workflow versions."""

    versions: List[WorkflowVersion]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowVersionListResponse:
        return cls(
            versions=[WorkflowVersion.from_dict(v) for v in (data.get("versions") or [])],
        )


@dataclass
class RunResponse:
    """Response from running a workflow."""

    workflow_request_id: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RunResponse:
        return cls(workflow_request_id=data["workflow_request_id"])


@dataclass
class ExecutionTreeResponse:
    """Response from getting an execution tree."""

    execution_tree: ExecutionTree

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionTreeResponse:
        return cls(execution_tree=ExecutionTree.from_dict(data["execution_tree"]))


@dataclass
class HistoryResponse:
    """Response from getting workflow history."""

    data: List[WorkflowRequest]
    pagination: Pagination

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> HistoryResponse:
        return cls(
            data=[WorkflowRequest.from_dict(d) for d in (raw.get("data") or [])],
            pagination=Pagination.from_dict(raw["pagination"]),
        )


@dataclass
class ChatHistoryResponse:
    """Response from getting paginated chat message history."""

    messages: List[ChatMessage]
    has_more: bool

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> ChatHistoryResponse:
        return cls(
            messages=[ChatMessage.from_dict(m) for m in (raw.get("messages") or [])],
            has_more=raw.get("has_more", False),
        )


@dataclass
class EventResponse:
    """Response from sending a webhook event."""

    ok: bool
    event_id: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EventResponse:
        return cls(ok=data["ok"], event_id=data["event_id"])


@dataclass
class SSEEvent:
    """A single Server-Sent Event from a listen stream.

    For chat events, check the `event_type` field:
    - "text_delta": `text_delta` contains the streamed text chunk
    - "reasoning_delta": `reasoning_delta` contains thinking text
    - "tool_call_start": Tool call initiated (`tool_call_id`, `tool_name`)
    - "tool_call_delta": Tool call args delta (`tool_call_id`, `tool_args_delta`)
    - "tool_start": Tool execution started (`tool_name`, `tool_call_id`)
    - "tool_complete": Tool finished (`tool_name`, `tool_call_id`, `tool_result`)
    - "tool_error": Tool failed (`tool_name`, `tool_call_id`, `error`)
    - "tool_approval_request": Approval needed (`tool_name`, `tool_call_id`, `tool_args`)
    - "tool_approval_response": Approval result (`tool_name`, `tool_call_id`, `approved`)
    - "user_message": Voice transcript (`text`)
    - "done": Iteration complete
    - "stopped": User stopped workflow
    - "error": Error occurred (`error`)
    - None: Check `workflow_request` and `node_execution` for status updates
    """

    workflow_request: Optional[WorkflowRequest] = None
    node_execution: Optional[NodeExecution] = None
    is_keepalive: bool = False
    raw_data: Optional[str] = None

    # Event type and metadata
    event_type: Optional[str] = None
    iteration: Optional[int] = None
    run_id: Optional[str] = None

    # Text streaming
    text_delta: Optional[str] = None

    # Reasoning/thinking
    reasoning_delta: Optional[str] = None
    reasoning_type: Optional[str] = None

    # Tool calls
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args_delta: Optional[str] = None
    tool_args: Optional[Any] = None
    tool_result: Optional[Any] = None

    # Tool approval
    approved: Optional[bool] = None

    # Messages and errors
    text: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SSEEvent:
        wr = None
        ne = None
        if "workflow_request" in data and data["workflow_request"]:
            wr = WorkflowRequest.from_dict(data["workflow_request"])
        if "node_execution" in data and data["node_execution"]:
            ne = NodeExecution.from_dict(data["node_execution"])

        event_type = data.get("type")

        return cls(
            workflow_request=wr,
            node_execution=ne,
            event_type=event_type,
            iteration=data.get("iteration"),
            run_id=data.get("run_id"),
            # Text streaming
            text_delta=data.get("delta"),
            # Reasoning
            reasoning_delta=data.get("reasoning_delta"),
            reasoning_type=data.get("reasoning_type"),
            # Tool calls
            tool_call_id=data.get("tool_call_id"),
            tool_name=data.get("tool_name"),
            tool_args_delta=data.get("tool_args_delta"),
            tool_args=data.get("args"),
            tool_result=data.get("result"),
            # Approval
            approved=data.get("approved"),
            # Messages/errors
            text=data.get("text"),
            message=data.get("message"),
            error=data.get("error"),
        )


# --- Billing / Cost Tracking ---


@dataclass
class UserBalance:
    """User's current balance."""

    balance_microdollars: int
    balance_usd: float
    currency: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserBalance:
        return cls(
            balance_microdollars=data["balance_microdollars"],
            balance_usd=data["balance_usd"],
            currency=data["currency"],
        )


@dataclass
class BalanceTransaction:
    """A single balance transaction (credit, debit, or refund)."""

    id: str
    user_id: str
    amount: int
    currency: str
    type: str
    status: str
    created_at: str
    updated_at: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_charge_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BalanceTransaction:
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            amount=data["amount"],
            currency=data["currency"],
            type=data["type"],
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            description=data.get("description"),
            metadata=data.get("metadata"),
            stripe_payment_intent_id=data.get("stripe_payment_intent_id"),
            stripe_charge_id=data.get("stripe_charge_id"),
        )


@dataclass
class TransactionPagination:
    """Offset-based pagination for transaction history."""

    page: int
    limit: int
    total_count: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TransactionPagination:
        return cls(
            page=data["page"],
            limit=data["limit"],
            total_count=data["total_count"],
            total_pages=data["total_pages"],
            has_next=data["has_next"],
            has_prev=data["has_prev"],
        )


@dataclass
class TransactionHistoryResponse:
    """Response from getting transaction history."""

    transactions: List[BalanceTransaction]
    pagination: TransactionPagination

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TransactionHistoryResponse:
        return cls(
            transactions=[
                BalanceTransaction.from_dict(t) for t in (data.get("transactions") or [])
            ],
            pagination=TransactionPagination.from_dict(data["pagination"]),
        )


@dataclass
class ActivityStats:
    """Aggregate activity statistics for the authenticated user."""

    balance: float
    total_requests: int
    total_spending: float
    avg_cost_per_request: float
    input_tokens: int
    output_tokens: int
    total_tokens: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ActivityStats:
        return cls(
            balance=data["balance"],
            total_requests=data["total_requests"],
            total_spending=data["total_spending"],
            avg_cost_per_request=data["avg_cost_per_request"],
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
        )


@dataclass
class DailyActivity:
    """Activity data for a single day."""

    date: str
    total_cost: float
    request_count: int
    node_count: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DailyActivity:
        return cls(
            date=data["date"],
            total_cost=data["total_cost"],
            request_count=data["request_count"],
            node_count=data["node_count"],
        )


@dataclass
class DailyActivityResponse:
    """Response from getting daily activity data."""

    data: List[DailyActivity]
    days: int

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> DailyActivityResponse:
        return cls(
            data=[DailyActivity.from_dict(d) for d in (raw.get("data") or [])],
            days=raw["days"],
        )


# --- Memory ---


@dataclass
class MemoryMessage:
    """A single message in node context memory."""

    id: str
    role: str
    content: Any = None
    context_memory_id: Optional[str] = None
    agent_node_id: Optional[str] = None
    workflow_version_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    files: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryMessage:
        return cls(
            id=data["id"],
            role=data["role"],
            content=data.get("content"),
            context_memory_id=data.get("context_memory_id"),
            agent_node_id=data.get("agent_node_id"),
            workflow_version_id=data.get("workflow_version_id"),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            files=data.get("files"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class MemoryInstance:
    """A unique memory instance (context_memory_id + agent_node_id pair)."""

    id: str
    name: str
    workflow_version_id: str
    chat_id: str
    memory_node_id: str
    memory_node_label: str
    context_size: int
    message_count: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryInstance:
        return cls(
            id=data["id"],
            name=data["name"],
            workflow_version_id=data["workflow_version_id"],
            chat_id=data["chat_id"],
            memory_node_id=data["memory_node_id"],
            memory_node_label=data["memory_node_label"],
            context_size=data.get("context_size", 0),
            message_count=data.get("message_count", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class MemoryListResponse:
    """Response from listing memory instances for a workflow version."""

    chats: List[MemoryInstance]
    next_cursor: Optional[str] = None
    has_more: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryListResponse:
        return cls(
            chats=[MemoryInstance.from_dict(c) for c in (data.get("chats") or [])],
            next_cursor=data.get("next_cursor"),
            has_more=data.get("has_more", False),
        )


@dataclass
class MemoryGetResponse:
    """Response from getting paginated memory messages."""

    messages: List[MemoryMessage]
    next_cursor: Optional[str] = None
    has_more: bool = False
    limit: int = 20

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryGetResponse:
        return cls(
            messages=[MemoryMessage.from_dict(m) for m in (data.get("messages") or [])],
            next_cursor=data.get("next_cursor"),
            has_more=data.get("has_more", False),
            limit=data.get("limit", 20),
        )


@dataclass
class MemoryActionResponse:
    """Response from a memory action (summarize, trim, clear, export)."""

    action: str
    message: str
    deleted_count: int = 0
    summary: Optional[str] = None
    messages: Optional[List[MemoryMessage]] = None
    remaining_count: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryActionResponse:
        msgs = None
        if data.get("messages"):
            msgs = [MemoryMessage.from_dict(m) for m in data["messages"]]
        return cls(
            action=data["action"],
            message=data["message"],
            deleted_count=data.get("deleted_count", 0),
            summary=data.get("summary"),
            messages=msgs,
            remaining_count=data.get("remaining_count", 0),
        )


# ---------------------------------------------------------------------------
# MCP Catalog
# ---------------------------------------------------------------------------


@dataclass
class MCPCatalogItem:
    """An MCP server from the catalog."""

    id: str
    name: str
    url: str
    transport_type: str
    auth_type: str
    is_featured: bool
    created_at: str
    updated_at: str
    description: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    display_order: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPCatalogItem:
        return cls(
            id=data["id"],
            name=data["name"],
            url=data["url"],
            transport_type=data["transport_type"],
            auth_type=data["auth_type"],
            is_featured=data.get("is_featured", False),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            description=data.get("description"),
            auth_config=data.get("auth_config"),
            image_url=data.get("image_url"),
            category=data.get("category"),
            display_order=data.get("display_order"),
        )


@dataclass
class MCPCatalogListResponse:
    """Paginated list of MCP catalog items."""

    mcp_servers: List[MCPCatalogItem]
    current_page: int
    per_page: int
    total_count: int
    total_pages: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPCatalogListResponse:
        return cls(
            mcp_servers=[MCPCatalogItem.from_dict(s) for s in (data.get("mcp_servers") or [])],
            current_page=data.get("current_page", 1),
            per_page=data.get("per_page", 20),
            total_count=data.get("total_count", 0),
            total_pages=data.get("total_pages", 0),
        )


# ---------------------------------------------------------------------------
# MCP Connections
# ---------------------------------------------------------------------------


@dataclass
class MCPConnection:
    """An end-user MCP server connection."""

    id: str
    user_id: str
    name: str
    url: str
    transport_type: str
    auth_type: str
    created_at: str
    image_url: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    end_user_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPConnection:
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            name=data["name"],
            url=data["url"],
            transport_type=data["transport_type"],
            auth_type=data["auth_type"],
            created_at=data.get("created_at", ""),
            image_url=data.get("image_url"),
            auth_config=data.get("auth_config"),
            end_user_id=data.get("end_user_id"),
        )


@dataclass
class MCPConnectionListResponse:
    """List of MCP connections with total count."""

    connections: List[MCPConnection]
    total: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPConnectionListResponse:
        return cls(
            connections=[MCPConnection.from_dict(c) for c in (data.get("connections") or [])],
            total=data.get("total", 0),
        )


@dataclass
class MCPExecuteToolResult:
    """Raw result returned by an MCP tool call."""

    content: Optional[List[Dict[str, Any]]] = None
    structured_content: Optional[Any] = None
    is_error: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPExecuteToolResult:
        return cls(
            content=data.get("content"),
            structured_content=data.get("structuredContent"),
            is_error=data.get("isError", False),
        )


@dataclass
class MCPExecuteToolResponse:
    """Response for direct MCP tool execution."""

    result: MCPExecuteToolResult
    is_error: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPExecuteToolResponse:
        return cls(
            result=MCPExecuteToolResult.from_dict(data.get("result") or {}),
            is_error=data.get("is_error", False),
        )


@dataclass
class UserMCPServer:
    id: str
    user_id: str
    name: str
    url: str
    transport_type: str
    auth_type: str
    created_at: str
    updated_at: str
    image_url: Optional[str] = None
    is_system: Optional[bool] = None
    credential_expires_at: Optional[str] = None
    status: Optional[str] = None
    has_credential: Optional[bool] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserMCPServer:
        return cls(
            id=data.get("id", ""),
            user_id=data.get("user_id", ""),
            name=data.get("name", ""),
            url=data.get("url", ""),
            transport_type=data.get("transport_type", ""),
            auth_type=data.get("auth_type", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            image_url=data.get("image_url"),
            is_system=data.get("is_system"),
            credential_expires_at=data.get("credential_expires_at"),
            status=data.get("status"),
            has_credential=data.get("has_credential"),
        )


@dataclass
class UserMCPServerListResponse:
    servers: List[UserMCPServer]
    total: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserMCPServerListResponse:
        return cls(
            servers=[UserMCPServer.from_dict(s) for s in (data.get("servers") or [])],
            total=data.get("total", 0),
        )


@dataclass
class MCPServerToolOption:
    label: str
    value: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPServerToolOption:
        return cls(
            label=data.get("label", ""),
            value=data.get("value", ""),
        )


@dataclass
class MCPServerToolsResponse:
    options: List[MCPServerToolOption]
    total: int
    limit: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MCPServerToolsResponse:
        return cls(
            options=[MCPServerToolOption.from_dict(o) for o in (data.get("options") or [])],
            total=data.get("total", 0),
            limit=data.get("limit", 0),
        )
