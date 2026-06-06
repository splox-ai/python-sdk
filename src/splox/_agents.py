"""Agent spawn/gather helpers for sandbox child agents."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union

from splox._models import AgentResult
from splox._transport import AsyncTransport, SyncTransport

_TERMINAL_STATUSES = {"completed", "failed", "stopped"}


def _get_parent_run_id() -> str:
    parent_run_id = os.environ.get("SPLOX_RUN_ID")
    if not parent_run_id:
        raise RuntimeError(
            "SPLOX_RUN_ID environment variable is required to spawn an agent. "
            "Run this inside a Splox workflow sandbox or set SPLOX_RUN_ID to the parent run id."
        )
    return parent_run_id


class AgentError(Exception):
    """Raised when an agent run reaches a failed/stopped terminal state."""


class AgentRun:
    """Handle for an already-running child agent run."""

    def __init__(self, agents: "Agents", run_id: str) -> None:
        self._agents = agents
        self.run_id = str(run_id)

    def __str__(self) -> str:
        return self.run_id

    def __repr__(self) -> str:
        return f"AgentRun(run_id={self.run_id!r})"

    def poll(self) -> AgentResult:
        """Return a non-blocking snapshot for this run."""
        results = self._agents.gather([self], timeout=0, _wait_seconds=0)
        if results:
            return results[0]
        return AgentResult(run_id=self.run_id, status="pending")

    def result(self, timeout: Optional[float] = None) -> str:
        """Block until this run is terminal and return its final message."""
        results = self._agents.gather([self], timeout=timeout)
        current = results[0] if results else AgentResult(run_id=self.run_id, status="pending")
        if current.status == "completed":
            return current.result or ""
        if current.status in {"failed", "stopped"}:
            raise AgentError(current.error or current.status)
        raise TimeoutError(f"agent run {self.run_id} did not finish before timeout")


class AsyncAgentRun:
    """Async handle for an already-running child agent run."""

    def __init__(self, agents: "AsyncAgents", run_id: str) -> None:
        self._agents = agents
        self.run_id = str(run_id)

    def __str__(self) -> str:
        return self.run_id

    def __repr__(self) -> str:
        return f"AsyncAgentRun(run_id={self.run_id!r})"

    async def poll(self) -> AgentResult:
        results = await self._agents.gather([self], timeout=0, _wait_seconds=0)
        if results:
            return results[0]
        return AgentResult(run_id=self.run_id, status="pending")

    async def result(self, timeout: Optional[float] = None) -> str:
        results = await self._agents.gather([self], timeout=timeout)
        current = results[0] if results else AgentResult(run_id=self.run_id, status="pending")
        if current.status == "completed":
            return current.result or ""
        if current.status in {"failed", "stopped"}:
            raise AgentError(current.error or current.status)
        raise TimeoutError(f"agent run {self.run_id} did not finish before timeout")


def _run_id(run: Union[AgentRun, AsyncAgentRun, str]) -> str:
    return run.run_id if hasattr(run, "run_id") else str(run)


def _ordered_results(run_ids: Sequence[str], items: Iterable[Dict[str, Any]]) -> List[AgentResult]:
    by_id = {str(item.get("run_id")): AgentResult.from_dict(item) for item in items}
    return [by_id.get(rid, AgentResult(run_id=rid, status="pending")) for rid in run_ids]


class Agents:
    """Synchronous agent spawn/gather operations."""

    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def spawn(
        self,
        message: str,
        agent_name: str,
        conversation_id: Optional[str] = None,
        label: Optional[str] = None,
    ) -> AgentRun:
        """Spawn a child agent run by agent tool name and return an AgentRun handle."""
        if not agent_name:
            raise ValueError("agent_name is required")
        payload: Dict[str, str] = {
            "parent_run_id": _get_parent_run_id(),
            "message": message,
            "agent_name": agent_name,
        }
        if conversation_id is not None:
            payload["conversation_id"] = conversation_id
        if label is not None:
            payload["label"] = label
        data = self._t.request("POST", "/agents/spawn", json_body=payload)
        return AgentRun(self, str(data["run_id"]))

    def gather(
        self,
        runs: Sequence[Union[AgentRun, str]],
        timeout: Optional[float] = None,
        *,
        timeout_seconds: Optional[float] = None,
        poll_interval: float = 2,
        _wait_seconds: float = 5,
    ) -> List[AgentResult]:
        """Gather AgentRun handles or run_id strings without raising on agent failure."""
        if timeout is None and timeout_seconds is not None:
            timeout = timeout_seconds
        run_ids = [_run_id(r) for r in runs]
        if not run_ids:
            return []
        started = time.monotonic()
        results = [AgentResult(run_id=rid, status="pending") for rid in run_ids]
        while True:
            now = time.monotonic()
            remaining = None if timeout is None else max(0.0, timeout - (now - started))
            wait_seconds = min(25.0, max(0.0, float(_wait_seconds)))
            if remaining is not None:
                wait_seconds = min(wait_seconds, remaining)
            request_timeout = max(5.0, wait_seconds + 10.0)
            request_started = time.monotonic()
            data = self._t.request(
                "POST",
                "/agents/gather",
                json_body={"run_ids": run_ids, "wait_seconds": wait_seconds},
                timeout=request_timeout,
            )
            results = _ordered_results(run_ids, data.get("results") or [])
            if data.get("all_terminal"):
                return results
            if timeout is not None and time.monotonic() - started >= timeout:
                return results
            elapsed_request = time.monotonic() - request_started
            if poll_interval > 0 and elapsed_request < poll_interval:
                time.sleep(poll_interval - elapsed_request)


class AsyncAgents:
    """Asynchronous agent spawn/gather operations."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def spawn(
        self,
        message: str,
        agent_name: str,
        conversation_id: Optional[str] = None,
        label: Optional[str] = None,
    ) -> AsyncAgentRun:
        """Spawn a child agent run by agent tool name and return an async AgentRun handle."""
        if not agent_name:
            raise ValueError("agent_name is required")
        payload: Dict[str, str] = {
            "parent_run_id": _get_parent_run_id(),
            "message": message,
            "agent_name": agent_name,
        }
        if conversation_id is not None:
            payload["conversation_id"] = conversation_id
        if label is not None:
            payload["label"] = label
        data = await self._t.request("POST", "/agents/spawn", json_body=payload)
        return AsyncAgentRun(self, str(data["run_id"]))

    async def gather(
        self,
        runs: Sequence[Union[AsyncAgentRun, str]],
        timeout: Optional[float] = None,
        *,
        timeout_seconds: Optional[float] = None,
        poll_interval: float = 2,
        _wait_seconds: float = 5,
    ) -> List[AgentResult]:
        """Gather async AgentRun handles or run_id strings without raising on agent failure."""
        if timeout is None and timeout_seconds is not None:
            timeout = timeout_seconds
        run_ids = [_run_id(r) for r in runs]
        if not run_ids:
            return []
        started = time.monotonic()
        results = [AgentResult(run_id=rid, status="pending") for rid in run_ids]
        while True:
            now = time.monotonic()
            remaining = None if timeout is None else max(0.0, timeout - (now - started))
            wait_seconds = min(25.0, max(0.0, float(_wait_seconds)))
            if remaining is not None:
                wait_seconds = min(wait_seconds, remaining)
            request_timeout = max(5.0, wait_seconds + 10.0)
            request_started = time.monotonic()
            data = await self._t.request(
                "POST",
                "/agents/gather",
                json_body={"run_ids": run_ids, "wait_seconds": wait_seconds},
                timeout=request_timeout,
            )
            results = _ordered_results(run_ids, data.get("results") or [])
            if data.get("all_terminal"):
                return results
            if timeout is not None and time.monotonic() - started >= timeout:
                return results
            elapsed_request = time.monotonic() - request_started
            if poll_interval > 0 and elapsed_request < poll_interval:
                await asyncio.sleep(poll_interval - elapsed_request)
