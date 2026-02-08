# Splox Python SDK

Official Python SDK for the [Splox API](https://docs.splox.io) — run workflows, manage chats, and monitor execution programmatically.

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

```python
# Sync
for event in client.chats.listen(chat_id):
    print(event)

# Async
async for event in async_client.chats.listen(chat_id):
    print(event)
```

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

## License

MIT
