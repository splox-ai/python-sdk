"""Integration test — runs the SDK against the live Splox API.

Requires environment variables:
    SPLOX_API_KEY          — API token for authentication
    SPLOX_BASE_URL         — (optional) API base URL, defaults to https://app.splox.io/api/v1
    SPLOX_TEST_WORKFLOW    — (optional) workflow name to search for, defaults to "Test"
"""

import asyncio
import os
import sys

from splox import AsyncSploxClient, SploxClient

API_KEY = os.environ.get("SPLOX_API_KEY", "")
BASE_URL = os.environ.get("SPLOX_BASE_URL", "https://app.splox.io/api/v1")
WORKFLOW_NAME = os.environ.get("SPLOX_TEST_WORKFLOW", "Test")

if not API_KEY:
    print("ERROR: SPLOX_API_KEY environment variable is required")
    print("  export SPLOX_API_KEY=your-api-key")
    sys.exit(1)


def _print_tree(tree) -> None:
    for node in tree.nodes:
        output_preview = ""
        if node.output_data:
            text = str(node.output_data)
            output_preview = f" → {text[:80]}{'…' if len(text) > 80 else ''}"
        print(f"      [{node.status}] {node.node_label} ({node.node_type}){output_preview}")


def test_sync() -> None:
    print("=" * 60)
    print("SYNC CLIENT TESTS")
    print("=" * 60)

    with SploxClient(api_key=API_KEY, base_url=BASE_URL) as client:

        # 1. List workflows
        print("1) Listing workflows...")
        wf_list = client.workflows.list(limit=20)
        assert len(wf_list.workflows) > 0
        print(f"   ✅ Found {len(wf_list.workflows)} workflow(s)")
        for wf in wf_list.workflows:
            name = wf.latest_version.name if wf.latest_version else "(no version)"
            print(f"      • {wf.id[:12]}… — {name}")

        # 2. Search for the "Test" workflow by name
        print(f'2) Searching for workflow "{WORKFLOW_NAME}"...')
        search_resp = client.workflows.list(search=WORKFLOW_NAME)
        assert len(search_resp.workflows) > 0, f'No workflow named "{WORKFLOW_NAME}" found'
        test_wf = search_resp.workflows[0]
        workflow_id = test_wf.id
        print(f"   ✅ Found: {workflow_id}")

        # 3. Get specific workflow
        print("3) Getting workflow by ID...")
        wf_full = client.workflows.get(workflow_id)
        assert wf_full.workflow.id == workflow_id
        print(f"   ✅ Got workflow: {wf_full.workflow_version.name}")
        print(f"      Nodes: {len(wf_full.nodes)}, Edges: {len(wf_full.edges)}")
        for n in wf_full.nodes:
            print(f"      • [{n.node_type}] {n.label} ({n.id[:12]}…)")

        # 4. Get latest version
        print("4) Getting latest version...")
        version = client.workflows.get_latest_version(workflow_id)
        assert version.workflow_id == workflow_id
        print(f"   ✅ Latest version: {version.id} (v{version.version_number}, status={version.status})")

        # 5. Get start nodes
        print("5) Getting start nodes...")
        start_nodes_resp = client.workflows.get_start_nodes(version.id)
        assert len(start_nodes_resp.nodes) > 0
        start_node = start_nodes_resp.nodes[0]
        print(f"   ✅ Found {len(start_nodes_resp.nodes)} start node(s)")
        for sn in start_nodes_resp.nodes:
            print(f"      • {sn.id} — {sn.label}")

        # 6. Full programmatic flow (no hardcoded IDs)
        print("6) Full programmatic flow (discover → run → wait)...")

        # Create chat + run
        chat = client.chats.create(
            name="Programmatic Flow Test",
            resource_id=workflow_id,
        )
        result = client.workflows.run(
            workflow_version_id=version.id,
            chat_id=chat.id,
            start_node_id=start_node.id,
            query="Hello from fully programmatic SDK test!",
        )
        print(f"   ▶ Workflow {result.workflow_request_id} started")

        # Wait for completion
        for event in client.workflows.listen(result.workflow_request_id):
            if event.is_keepalive:
                continue
            if event.workflow_request and event.workflow_request.status in ("completed", "failed", "stopped"):
                print(f"   ✅ Completed with status: {event.workflow_request.status}")
                break

        tree_resp = client.workflows.get_execution_tree(result.workflow_request_id)
        _print_tree(tree_resp.execution_tree)

        # 7. Chat listen
        print("7) Testing chat.listen() SSE...")
        result2 = client.workflows.run(
            workflow_version_id=version.id,
            chat_id=chat.id,
            start_node_id=start_node.id,
            query="Second message for chat listen test",
        )
        chat_event_count = 0
        for event in client.chats.listen(chat.id):
            if event.is_keepalive:
                continue
            chat_event_count += 1
            if event.workflow_request and event.workflow_request.status in ("completed", "failed", "stopped"):
                break
        print(f"   ✅ Chat listen done — {chat_event_count} events")

        # 8. Stop workflow
        print("8) Testing workflow stop...")
        result3 = client.workflows.run(
            workflow_version_id=version.id,
            chat_id=chat.id,
            start_node_id=start_node.id,
            query="This should be stopped",
        )
        try:
            client.workflows.stop(result3.workflow_request_id)
            print(f"   ✅ Stop sent for: {result3.workflow_request_id}")
        except Exception as e:
            print(f"   ⚠️  Stop result: {e}")

        # 9. run_and_wait
        print("9) Testing run_and_wait()...")
        chat2 = client.chats.create(name="run_and_wait test", resource_id=workflow_id)
        tree_resp2 = client.workflows.run_and_wait(
            workflow_version_id=version.id,
            chat_id=chat2.id,
            start_node_id=start_node.id,
            query="Run and wait test",
            timeout=120,
        )
        assert tree_resp2.execution_tree.status in ("completed", "failed", "stopped")
        print(f"   ✅ run_and_wait completed: {tree_resp2.execution_tree.status}")

        # 10. History
        print("10) Getting history...")
        history = client.workflows.get_history(result.workflow_request_id, limit=5)
        print(f"   ✅ History: {len(history.data)} entries")

        # 11. List workflow versions
        print("11) Listing workflow versions...")
        versions_resp = client.workflows.list_versions(workflow_id)
        assert len(versions_resp.versions) > 0
        print(f"   ✅ Found {len(versions_resp.versions)} version(s)")
        for v in versions_resp.versions:
            print(f"      • v{v.version_number} ({v.id[:12]}…) status={v.status}")

        # 12. List chats for resource
        print("12) Listing chats for workflow...")
        chat_list = client.chats.list_for_resource("api", workflow_id)
        assert len(chat_list.chats) > 0
        print(f"   ✅ Found {len(chat_list.chats)} chat(s)")

        # 13. Get chat history (messages)
        print("13) Getting chat message history...")
        history_resp = client.chats.get_history(chat.id, limit=10)
        print(f"   ✅ Got {len(history_resp.messages)} message(s) (has_more={history_resp.has_more})")
        for msg in history_resp.messages[:3]:
            preview = ""
            if msg.content:
                text = msg.content[0].text or msg.content[0].type
                preview = f" — {text[:60]}{'…' if len(text) > 60 else ''}"
            print(f"      • [{msg.role}]{preview}")

        # 14. Delete chat history
        print("14) Deleting chat history...")
        cleanup_chat = client.chats.create(name="Cleanup Test", resource_id=workflow_id)
        client.chats.delete_history(cleanup_chat.id)
        print(f"   ✅ Chat history deleted for {cleanup_chat.id}")

        # 15. Delete chat
        print("15) Deleting chat session...")
        client.chats.delete(cleanup_chat.id)
        print(f"   ✅ Chat deleted: {cleanup_chat.id}")

    print("\n✅ All sync tests passed!\n")


async def test_async() -> None:
    print("=" * 60)
    print("ASYNC CLIENT TESTS")
    print("=" * 60)

    async with AsyncSploxClient(api_key=API_KEY, base_url=BASE_URL) as client:

        # 1. Search for the "Test" workflow
        print(f'1) Searching for workflow "{WORKFLOW_NAME}" (async)...')
        search_resp = await client.workflows.list(search=WORKFLOW_NAME)
        assert len(search_resp.workflows) > 0
        test_wf = search_resp.workflows[0]
        workflow_id = test_wf.id
        print(f"   ✅ Found: {workflow_id}")

        # 2. Get workflow
        print("2) Getting workflow (async)...")
        wf_full = await client.workflows.get(workflow_id)
        assert wf_full.workflow.id == workflow_id
        print(f"   ✅ Got: {wf_full.workflow_version.name} ({len(wf_full.nodes)} nodes)")

        # 3. Get latest version
        print("3) Getting latest version (async)...")
        latest = await client.workflows.get_latest_version(workflow_id)
        print(f"   ✅ v{latest.version_number}, status={latest.status}")

        # 4. Get start nodes
        print("4) Getting start nodes (async)...")
        start_nodes = await client.workflows.get_start_nodes(latest.id)
        assert len(start_nodes.nodes) > 0
        start_node = start_nodes.nodes[0]
        print(f"   ✅ Start node: {start_node.id} — {start_node.label}")

        # 5. Full programmatic flow (async)
        print("5) Full async programmatic flow...")
        chat = await client.chats.create(
            name="Async Programmatic Test",
            resource_id=workflow_id,
        )
        result = await client.workflows.run(
            workflow_version_id=latest.id,
            chat_id=chat.id,
            start_node_id=start_node.id,
            query="Hello from async programmatic test!",
        )
        print(f"   ▶ Started: {result.workflow_request_id}")

        async for event in client.workflows.listen(result.workflow_request_id):
            if event.is_keepalive:
                continue
            if event.workflow_request and event.workflow_request.status in ("completed", "failed", "stopped"):
                print(f"   ✅ Completed: {event.workflow_request.status}")
                break

        tree_resp = await client.workflows.get_execution_tree(result.workflow_request_id)
        _print_tree(tree_resp.execution_tree)

        # 6. Chat listen (async)
        print("6) Testing chat.listen() async...")
        result2 = await client.workflows.run(
            workflow_version_id=latest.id,
            chat_id=chat.id,
            start_node_id=start_node.id,
            query="Async chat listen test",
        )
        chat_event_count = 0
        async for event in client.chats.listen(chat.id):
            if event.is_keepalive:
                continue
            chat_event_count += 1
            if event.workflow_request and event.workflow_request.status in ("completed", "failed", "stopped"):
                break
        print(f"   ✅ Chat listen done — {chat_event_count} events")

        # 7. run_and_wait (async)
        print("7) Testing async run_and_wait()...")
        chat2 = await client.chats.create(name="Async run_and_wait", resource_id=workflow_id)
        tree_resp2 = await client.workflows.run_and_wait(
            workflow_version_id=latest.id,
            chat_id=chat2.id,
            start_node_id=start_node.id,
            query="Async run and wait test",
            timeout=120,
        )
        assert tree_resp2.execution_tree.status in ("completed", "failed", "stopped")
        print(f"   ✅ run_and_wait: {tree_resp2.execution_tree.status}")

        # 8. List workflow versions (async)
        print("8) Listing workflow versions (async)...")
        versions_resp = await client.workflows.list_versions(workflow_id)
        assert len(versions_resp.versions) > 0
        print(f"   ✅ Found {len(versions_resp.versions)} version(s)")

        # 9. List chats for resource (async)
        print("9) Listing chats for workflow (async)...")
        chat_list = await client.chats.list_for_resource("api", workflow_id)
        assert len(chat_list.chats) > 0
        print(f"   ✅ Found {len(chat_list.chats)} chat(s)")

        # 10. Get chat history (async)
        print("10) Getting chat message history (async)...")
        history_resp = await client.chats.get_history(chat.id, limit=10)
        print(f"   ✅ Got {len(history_resp.messages)} message(s) (has_more={history_resp.has_more})")

        # 11. Delete chat history (async)
        print("11) Deleting chat history (async)...")
        cleanup_chat = await client.chats.create(name="Async Cleanup", resource_id=workflow_id)
        await client.chats.delete_history(cleanup_chat.id)
        print(f"   ✅ Chat history deleted")

        # 12. Delete chat (async)
        print("12) Deleting chat session (async)...")
        await client.chats.delete(cleanup_chat.id)
        print(f"   ✅ Chat deleted")

    print("\n✅ All async tests passed!\n")


def main() -> None:
    test_sync()
    asyncio.run(test_async())
    print("🎉 ALL INTEGRATION TESTS PASSED!")


if __name__ == "__main__":
    main()
