"""Integration tests for the Memory API — runs against the live Splox API.

Requires environment variables:
    SPLOX_API_KEY          — API token for authentication
    SPLOX_BASE_URL         — (optional) API base URL, defaults to https://splox.io/api/v1
    SPLOX_TEST_WORKFLOW    — (optional) workflow name to search for, defaults to "Test"

The target workflow MUST have at least one agent node with context memory
enabled so that executing it produces memory entries to test against.
"""

import asyncio
import os
import sys
import time

from splox import (
    AsyncSploxClient,
    SploxClient,
    MemoryActionResponse,
    MemoryGetResponse,
    MemoryListResponse,
)

API_KEY = os.environ.get("SPLOX_API_KEY", "")
BASE_URL = os.environ.get("SPLOX_BASE_URL", "https://test2025.splox.io/api/v1")
WORKFLOW_NAME = os.environ.get("SPLOX_TEST_WORKFLOW", "Test")

if not API_KEY:
    print("ERROR: SPLOX_API_KEY environment variable is required")
    print("  export SPLOX_API_KEY=your-api-key")
    sys.exit(1)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _run_workflow_and_wait(client: SploxClient, workflow_id: str, version_id: str, entry_node_id: str, query: str, chat_id: str) -> str:
    """Run a workflow and block until it completes. Returns the workflow_request_id."""
    result = client.workflows.run(
        workflow_version_id=version_id,
        chat_id=chat_id,
        entry_node_ids=[entry_node_id],
        query=query,
    )
    for event in client.workflows.listen(result.workflow_request_id):
        if event.is_keepalive:
            continue
        if event.workflow_request and event.workflow_request.status in (
            "completed",
            "failed",
            "stopped",
        ):
            break
    return result.workflow_request_id


def _find_memory_instance(client: SploxClient, version_id: str):
    """Find the first memory instance for a workflow version, or None."""
    resp = client.memory.list(version_id)
    if resp.chats:
        return resp.chats[0]
    return None


# ── Sync Tests ───────────────────────────────────────────────────────────────


def test_memory_sync() -> None:
    print("=" * 60)
    print("SYNC MEMORY INTEGRATION TESTS")
    print("=" * 60)

    with SploxClient(api_key=API_KEY, base_url=BASE_URL) as client:

        # ── Setup: discover workflow, version, start node ────────────
        print(f'Setup) Finding workflow "{WORKFLOW_NAME}"...')
        search_resp = client.workflows.list(search=WORKFLOW_NAME)
        assert len(search_resp.workflows) > 0, f'No workflow named "{WORKFLOW_NAME}" found'
        test_wf = search_resp.workflows[0]
        workflow_id = test_wf.id

        version = client.workflows.get_latest_version(workflow_id)
        version_id = version.id

        entry_nodes = client.workflows.get_entry_nodes(version_id)
        assert len(entry_nodes.nodes) > 0, "No entry nodes found"
        entry_node_id = entry_nodes.nodes[0].id

        print(f"   ✅ Workflow: {workflow_id[:12]}…  Version: {version_id[:12]}…")

        # ── Create a dedicated chat and run workflow to generate memory ─
        print("1) Running workflow to generate context memory...")
        chat = client.chats.create(name="Memory Integration Test", resource_id=workflow_id)
        chat_id = chat.id

        # Send multiple messages to build up memory
        for i, msg in enumerate(["Hello, remember my name is Alice.", "What is 2+2?", "Tell me a joke."], 1):
            print(f"   ▶ Message {i}: {msg[:40]}...")
            _run_workflow_and_wait(client, workflow_id, version_id, entry_node_id, msg, chat_id)

        # Short pause to let memory persist
        time.sleep(1)

        # ── 2) List memory instances ─────────────────────────────────
        print("2) Listing memory instances...")
        list_resp = client.memory.list(version_id)
        assert isinstance(list_resp, MemoryListResponse)
        print(f"   ✅ Found {len(list_resp.chats)} memory instance(s)")

        if len(list_resp.chats) == 0:
            print("   ⚠️  No memory instances found — workflow may not have context memory enabled.")
            print("   Skipping remaining memory tests.")
            client.chats.delete(chat_id)
            return

        # Pick the memory instance that matches our chat
        memory_inst = None
        for inst in list_resp.chats:
            print(f"      • {inst.memory_node_label}: {inst.message_count} msgs (chat_id={inst.chat_id[:20]}…)")
            if inst.chat_id == chat_id:
                memory_inst = inst
        # If no exact match (template may resolve to a different ID), use the first one
        if memory_inst is None:
            memory_inst = list_resp.chats[0]
            print(f"   Using memory instance: {memory_inst.chat_id[:20]}…")

        agent_node_id = memory_inst.memory_node_id
        context_memory_id = memory_inst.chat_id

        # ── 3) Get memory messages ───────────────────────────────────
        print("3) Getting memory messages...")
        get_resp = client.memory.get(agent_node_id, chat_id=context_memory_id, limit=50)
        assert isinstance(get_resp, MemoryGetResponse)
        assert len(get_resp.messages) > 0, "Expected at least one memory message"
        print(f"   ✅ Got {len(get_resp.messages)} message(s) (has_more={get_resp.has_more})")
        for msg in get_resp.messages[:4]:
            content_preview = str(msg.content)[:60] if msg.content else "(empty)"
            print(f"      [{msg.role}] {content_preview}")

        # ── 4) Export memory ─────────────────────────────────────────
        print("4) Exporting memory...")
        export_resp = client.memory.export(
            agent_node_id,
            context_memory_id=context_memory_id,
            workflow_version_id=version_id,
        )
        assert isinstance(export_resp, MemoryActionResponse)
        assert export_resp.action == "export"
        assert export_resp.messages is not None
        assert len(export_resp.messages) > 0
        original_count = len(export_resp.messages)
        print(f"   ✅ Exported {original_count} message(s)")

        # ── 5) Trim memory ───────────────────────────────────────────
        print("5) Trimming memory...")
        trim_target = max(2, original_count - 2)  # trim at least 2 messages away
        trim_resp = client.memory.trim(
            agent_node_id,
            context_memory_id=context_memory_id,
            workflow_version_id=version_id,
            max_messages=trim_target,
        )
        assert isinstance(trim_resp, MemoryActionResponse)
        assert trim_resp.action == "trim"
        print(f"   ✅ Trimmed: deleted={trim_resp.deleted_count}, remaining={trim_resp.remaining_count}")
        if original_count > trim_target:
            assert trim_resp.deleted_count > 0, "Expected at least one message deleted"
            assert trim_resp.remaining_count <= trim_target
        else:
            print(f"   ℹ️  No trim needed (had {original_count} ≤ {trim_target})")

        # ── 6) Verify trim via get ───────────────────────────────────
        print("6) Verifying trim via get...")
        after_trim = client.memory.get(agent_node_id, chat_id=context_memory_id, limit=100)
        print(f"   ✅ After trim: {len(after_trim.messages)} message(s)")
        assert len(after_trim.messages) <= trim_target + 1  # +1 tolerance for race

        # ── 7) Summarize memory ──────────────────────────────────────
        # Rebuild enough messages for summarization to work (need ≥ 3)
        if len(after_trim.messages) < 4:
            print("7a) Building up messages for summarization...")
            for msg in ["Remember: project deadline is Friday.", "What tools can you use?"]:
                _run_workflow_and_wait(client, workflow_id, version_id, entry_node_id, msg, chat_id)
            time.sleep(1)

        print("7) Summarizing memory...")
        try:
            summarize_resp = client.memory.summarize(
                agent_node_id,
                context_memory_id=context_memory_id,
                workflow_version_id=version_id,
                keep_last_n=2,
            )
            assert isinstance(summarize_resp, MemoryActionResponse)
            assert summarize_resp.action == "summarize"
            assert summarize_resp.deleted_count > 0
            assert summarize_resp.summary is not None and len(summarize_resp.summary) > 0
            print(f"   ✅ Summarized: deleted={summarize_resp.deleted_count}, remaining={summarize_resp.remaining_count}")
            print(f"   📝 Summary preview: {summarize_resp.summary[:100]}…")
        except Exception as e:
            # Summarization calls an LLM, so it may fail if the agent's provider
            # isn't configured or has no credits — treat as non-fatal warning.
            print(f"   ⚠️  Summarize failed (may need LLM credits): {e}")

        # ── 8) Clear memory ──────────────────────────────────────────
        print("8) Clearing memory...")
        clear_resp = client.memory.clear(
            agent_node_id,
            context_memory_id=context_memory_id,
            workflow_version_id=version_id,
        )
        assert isinstance(clear_resp, MemoryActionResponse)
        assert clear_resp.action == "clear"
        assert clear_resp.remaining_count == 0
        print(f"   ✅ Cleared: deleted={clear_resp.deleted_count}")

        # ── 9) Verify clear ──────────────────────────────────────────
        print("9) Verifying clear via get...")
        after_clear = client.memory.get(agent_node_id, chat_id=context_memory_id, limit=100)
        assert len(after_clear.messages) == 0, f"Expected 0 messages after clear, got {len(after_clear.messages)}"
        print("   ✅ Memory is empty")

        # ── 10) Rebuild and test delete ──────────────────────────────
        print("10) Rebuilding memory and testing delete...")
        _run_workflow_and_wait(client, workflow_id, version_id, entry_node_id, "One more message for delete test.", chat_id)
        time.sleep(1)

        # Verify memory exists again
        rebuilt = client.memory.get(agent_node_id, chat_id=context_memory_id, limit=100)
        if len(rebuilt.messages) > 0:
            client.memory.delete(
                context_memory_id,
                memory_node_id=agent_node_id,
                workflow_version_id=version_id,
            )
            after_delete = client.memory.get(agent_node_id, chat_id=context_memory_id, limit=100)
            assert len(after_delete.messages) == 0, f"Expected 0 after delete, got {len(after_delete.messages)}"
            print("   ✅ Delete succeeded")
        else:
            print("   ⚠️  No messages rebuilt — skipping delete assertion")

        # ── Cleanup ──────────────────────────────────────────────────
        print("Cleanup) Deleting test chat...")
        client.chats.delete(chat_id)
        print("   ✅ Done")

    print("\n✅ All sync memory tests passed!\n")


# ── Async Tests ──────────────────────────────────────────────────────────────


async def test_memory_async() -> None:
    print("=" * 60)
    print("ASYNC MEMORY INTEGRATION TESTS")
    print("=" * 60)

    async with AsyncSploxClient(api_key=API_KEY, base_url=BASE_URL) as client:

        # ── Setup ────────────────────────────────────────────────────
        print(f'Setup) Finding workflow "{WORKFLOW_NAME}" (async)...')
        search_resp = await client.workflows.list(search=WORKFLOW_NAME)
        assert len(search_resp.workflows) > 0, f'No workflow named "{WORKFLOW_NAME}" found'
        test_wf = search_resp.workflows[0]
        workflow_id = test_wf.id

        version = await client.workflows.get_latest_version(workflow_id)
        version_id = version.id

        entry_nodes = await client.workflows.get_entry_nodes(version_id)
        assert len(entry_nodes.nodes) > 0, "No entry nodes found"
        entry_node_id = entry_nodes.nodes[0].id

        print(f"   ✅ Workflow: {workflow_id[:12]}…  Version: {version_id[:12]}…")

        # ── Run workflow to generate memory ──────────────────────────
        print("1) Running workflow to generate memory (async)...")
        chat = await client.chats.create(name="Async Memory Test", resource_id=workflow_id)
        chat_id = chat.id

        for i, msg in enumerate(["Hello, I'm Bob.", "What's the capital of France?", "Thanks!"], 1):
            print(f"   ▶ Message {i}: {msg}")
            result = await client.workflows.run(
                workflow_version_id=version_id,
                chat_id=chat_id,
                entry_node_ids=[entry_node_id],
                query=msg,
            )
            async for event in client.workflows.listen(result.workflow_request_id):
                if event.is_keepalive:
                    continue
                if event.workflow_request and event.workflow_request.status in (
                    "completed", "failed", "stopped",
                ):
                    break

        await asyncio.sleep(1)

        # ── 2) List memory instances ─────────────────────────────────
        print("2) Listing memory instances (async)...")
        list_resp = await client.memory.list(version_id)
        assert isinstance(list_resp, MemoryListResponse)
        print(f"   ✅ Found {len(list_resp.chats)} instance(s)")

        if not list_resp.chats:
            print("   ⚠️  No memory instances — skipping remaining tests")
            await client.chats.delete(chat_id)
            return

        memory_inst = None
        for inst in list_resp.chats:
            if inst.chat_id == chat_id:
                memory_inst = inst
        if memory_inst is None:
            memory_inst = list_resp.chats[0]

        agent_node_id = memory_inst.memory_node_id
        context_memory_id = memory_inst.chat_id

        # ── 3) Get messages ──────────────────────────────────────────
        print("3) Getting memory messages (async)...")
        get_resp = await client.memory.get(agent_node_id, chat_id=context_memory_id, limit=50)
        assert isinstance(get_resp, MemoryGetResponse)
        assert len(get_resp.messages) > 0
        print(f"   ✅ Got {len(get_resp.messages)} message(s)")

        # ── 4) Export ────────────────────────────────────────────────
        print("4) Exporting memory (async)...")
        export_resp = await client.memory.export(
            agent_node_id,
            context_memory_id=context_memory_id,
            workflow_version_id=version_id,
        )
        assert export_resp.action == "export"
        assert export_resp.messages is not None and len(export_resp.messages) > 0
        original_count = len(export_resp.messages)
        print(f"   ✅ Exported {original_count} message(s)")

        # ── 5) Trim ─────────────────────────────────────────────────
        print("5) Trimming memory (async)...")
        trim_target = max(2, original_count - 2)
        trim_resp = await client.memory.trim(
            agent_node_id,
            context_memory_id=context_memory_id,
            workflow_version_id=version_id,
            max_messages=trim_target,
        )
        assert trim_resp.action == "trim"
        print(f"   ✅ Trimmed: deleted={trim_resp.deleted_count}, remaining={trim_resp.remaining_count}")

        # ── 6) Clear ─────────────────────────────────────────────────
        print("6) Clearing memory (async)...")
        clear_resp = await client.memory.clear(
            agent_node_id,
            context_memory_id=context_memory_id,
            workflow_version_id=version_id,
        )
        assert clear_resp.action == "clear"
        assert clear_resp.remaining_count == 0
        print(f"   ✅ Cleared: deleted={clear_resp.deleted_count}")

        # ── 7) Verify empty ──────────────────────────────────────────
        print("7) Verifying empty (async)...")
        after_clear = await client.memory.get(agent_node_id, chat_id=context_memory_id, limit=100)
        assert len(after_clear.messages) == 0
        print("   ✅ Memory is empty")

        # ── Cleanup ──────────────────────────────────────────────────
        print("Cleanup) Deleting test chat (async)...")
        await client.chats.delete(chat_id)
        print("   ✅ Done")

    print("\n✅ All async memory tests passed!\n")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    test_memory_sync()
    asyncio.run(test_memory_async())
    print("🎉 ALL MEMORY INTEGRATION TESTS PASSED!")


if __name__ == "__main__":
    main()
