# Splox Python SDK

Official Python SDK for the [Splox API](https://docs.splox.io) — run workflows, manage chats, browse the MCP catalog, and monitor execution programmatically.

## Installation

```bash
pip install splox
```

## Quick Start

```python
from splox import SploxClient

client = SploxClient(api_key="your-api-key")

# Create a chat session
chat = client.chats.create(
    name="My Session",
    resource_id="your-workflow-id",
)

# Run a workflow
result = client.workflows.run(
    workflow_version_id="your-version-id",
    chat_id=chat.id,
    start_node_id="your-start-node-id",
    query="Summarize the latest sales report",
)

print(result.workflow_request_id)

# Get execution tree
tree = client.workflows.get_execution_tree(result.workflow_request_id)
for node in tree.execution_tree.nodes:
    print(f"{node.node_label}: {node.status}")
```

## Async Support

```python
import asyncio
from splox import AsyncSploxClient

async def main():
    client = AsyncSploxClient(api_key="your-api-key")

    chat = await client.chats.create(
        name="Async Session",
        resource_id="your-workflow-id",
    )

    result = await client.workflows.run(
        workflow_version_id="your-version-id",
        chat_id=chat.id,
        start_node_id="your-start-node-id",
        query="Hello from async!",
    )

    # Stream execution events via SSE
    async for event in client.workflows.listen(result.workflow_request_id):
        if event.node_execution:
            print(f"Node {event.node_execution.status}: {event.node_execution.output_data}")
        if event.workflow_request and event.workflow_request.status in ("completed", "failed"):
            break

    await client.close()

asyncio.run(main())
```

## Streaming (SSE)

### Listen to workflow execution

```python
# Sync
for event in client.workflows.listen(workflow_request_id):
    print(event)

# Async
async for event in async_client.workflows.listen(workflow_request_id):
    print(event)
```

### Listen to chat messages

Stream real-time chat events including text deltas, tool calls, and more:

```python
# Async example — collect streamed response
async for event in client.chats.listen(chat_id):
    if event.event_type == "text_delta":
        print(event.text_delta, end="", flush=True)
    elif event.event_type == "tool_call_start":
        print(f"\\nCalling tool: {event.tool_name}")
    elif event.event_type == "done":
        print("\\nIteration complete")
    
    # Stop when workflow completes
    if event.workflow_request and event.workflow_request.status == "completed":
        break
```

**Event types:**

| Type | Fields | Description |
|------|--------|-------------|
| `text_delta` | `text_delta` | Streamed text chunk |
| `reasoning_delta` | `reasoning_delta`, `reasoning_type` | Thinking content |
| `tool_call_start` | `tool_call_id`, `tool_name` | Tool call initiated |
| `tool_call_delta` | `tool_call_id`, `tool_args_delta` | Tool arguments delta |
| `tool_start` | `tool_name`, `tool_call_id` | Tool execution started |
| `tool_complete` | `tool_name`, `tool_call_id`, `tool_result` | Tool finished |
| `tool_error` | `tool_name`, `tool_call_id`, `error` | Tool failed |
| `done` | `iteration`, `run_id` | Iteration complete |
| `error` | `error` | Error occurred |

## Run & Wait

Convenience method that runs a workflow and waits for completion:

```python
execution = client.workflows.run_and_wait(
    workflow_version_id="your-version-id",
    chat_id=chat.id,
    start_node_id="your-start-node-id",
    query="Process this request",
    timeout=300,  # 5 minutes
)

print(execution.status)  # "completed"
for node in execution.nodes:
    print(f"{node.node_label}: {node.output_data}")
```

## Memory

Inspect and manage agent context memory — list instances, read messages, summarize, trim, clear, or export.

```python
# List memory instances (paginated)
result = client.memory.list("workflow-version-id", limit=20)
for inst in result.chats:
    print(f"{inst.memory_node_label}: {inst.message_count} messages")

# Paginate
if result.has_more:
    more = client.memory.list("workflow-version-id", cursor=result.next_cursor)

# Get messages for an agent node
messages = client.memory.get("agent-node-id", chat_id="session-id", limit=20)
for msg in messages.messages:
    print(f"[{msg.role}] {msg.content}")

# Summarize — compress older messages into an LLM-generated summary
result = client.memory.summarize(
    "agent-node-id",
    context_memory_id="session-id",
    workflow_version_id="version-id",
    keep_last_n=3,
)
print(f"Summary: {result.summary}")

# Trim — drop oldest messages to stay under a limit
client.memory.trim(
    "agent-node-id",
    context_memory_id="session-id",
    workflow_version_id="version-id",
    max_messages=20,
)

# Export all messages without modifying them
exported = client.memory.export(
    "agent-node-id",
    context_memory_id="session-id",
    workflow_version_id="version-id",
)

# Clear all messages
client.memory.clear(
    "agent-node-id",
    context_memory_id="session-id",
    workflow_version_id="version-id",
)

# Delete a specific memory instance
client.memory.delete(
    "session-id",
    memory_node_id="agent-node-id",
    workflow_version_id="version-id",
)
```

## MCP (Model Context Protocol)

Browse the MCP server catalog, manage end-user connections, and generate credential-submission links.

### Catalog

```python
# Search the MCP catalog
catalog = client.mcp.list_catalog(search="github", per_page=10)
for server in catalog.mcp_servers:
    print(f"{server.name} — {server.url}")

# Get featured servers
featured = client.mcp.list_catalog(featured=True)

# Get a single catalog item
item = client.mcp.get_catalog_item("mcp-server-id")
print(item.name, item.auth_type)
```

### Connections

```python
# List all end-user connections
conns = client.mcp.list_connections()
print(f"{conns.total} connections")

# List owner-user MCP servers via the same endpoint
owner_servers = client.mcp.list_connections(scope="owner_user")

# Filter by MCP server or end-user
filtered = client.mcp.list_connections(
    mcp_server_id="server-id",
    end_user_id="user-123",
)

# Delete a connection
client.mcp.delete_connection("connection-id")
```

### Connection Token & Link

Generate signed JWTs for end-user credential submission — no API call required:

```python
from splox import generate_connection_token, generate_connection_link

# Generate a token (expires in 1 hour)
token = generate_connection_token(
    mcp_server_id="mcp-server-id",
    owner_user_id="owner-user-id",
    end_user_id="end-user-id",
    credentials_encryption_key="your-credentials-encryption-key",
)

# Generate a full connection link
link = generate_connection_link(
    base_url="https://app.splox.io",
    mcp_server_id="mcp-server-id",
    owner_user_id="owner-user-id",
    end_user_id="end-user-id",
    credentials_encryption_key="your-credentials-encryption-key",
)
# → https://app.splox.io/tools/connect?token=eyJhbG...
```

Async usage is identical — the token/link functions are synchronous and available on both `client.mcp` and as standalone imports.

## Webhooks

```python
# Trigger a workflow via webhook (no auth required)
from splox import SploxClient

client = SploxClient()  # No API key needed for webhooks

result = client.events.send(
    webhook_id="your-webhook-id",
    payload={"order_id": "12345", "status": "paid"},
)
print(result.event_id)
```

## Error Handling

```python
from splox import SploxClient
from splox.exceptions import (
    SploxAPIError,
    SploxAuthError,
    SploxRateLimitError,
    SploxNotFoundError,
)

client = SploxClient(api_key="your-api-key")

try:
    result = client.workflows.run(...)
except SploxAuthError:
    print("Invalid or expired API token")
except SploxRateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after}")
except SploxNotFoundError:
    print("Resource not found")
except SploxAPIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## Custom Base URL

```python
client = SploxClient(
    api_key="your-api-key",
    base_url="https://your-self-hosted-instance.com/api/v1",
)
```

## API Reference

### `SploxClient` / `AsyncSploxClient`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str \| None` | `SPLOX_API_KEY` env | API authentication token |
| `base_url` | `str` | `https://app.splox.io/api/v1` | API base URL |
| `timeout` | `float` | `30.0` | Request timeout in seconds |

### `client.workflows`

| Method | Description |
|--------|-------------|
| `run(...)` | Trigger a workflow execution |
| `listen(id)` | Stream execution events (SSE) |
| `get_execution_tree(id)` | Get complete execution hierarchy |
| `get_history(id, ...)` | Get paginated execution history |
| `stop(id)` | Stop a running workflow |
| `run_and_wait(...)` | Run and wait for completion |

### `client.chats`

| Method | Description |
|--------|-------------|
| `create(...)` | Create a new chat session |
| `get(id)` | Get a chat by ID |
| `listen(id)` | Stream chat events (SSE) |

### `client.events`

| Method | Description |
|--------|-------------|
| `send(webhook_id, ...)` | Send event via webhook |

### `client.memory`

| Method | Description |
|--------|-------------|
| `list(version_id, ...)` | List memory instances (paginated) |
| `get(node_id, ...)` | Get paginated messages |
| `summarize(node_id, ...)` | Summarize older messages with LLM |
| `trim(node_id, ...)` | Drop oldest messages |
| `clear(node_id, ...)` | Remove all messages |
| `export(node_id, ...)` | Export all messages |
| `delete(memory_id, ...)` | Delete a memory instance |

### `client.mcp`

| Method | Description |
|--------|-------------|
| `list_catalog(...)` | Search/list MCP catalog (paginated) |
| `get_catalog_item(id)` | Get a single catalog item |
| `list_connections(...)` | List MCP links by identity scope (`end_user` or `owner_user`) |
| `delete_connection(id)` | Delete an end-user connection |
| `generate_connection_token(...)` | Create a signed JWT (1 hr expiry) |
| `generate_connection_link(...)` | Build a full connection URL |

### Standalone functions

| Function | Description |
|----------|-------------|
| `generate_connection_token(server_id, owner_id, end_user_id, key)` | Create a signed JWT |
| `generate_connection_link(base_url, server_id, owner_id, end_user_id, key)` | Build a full connection URL |

## License

MIT
