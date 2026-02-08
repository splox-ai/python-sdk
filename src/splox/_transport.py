"""Low-level HTTP transport for the Splox API."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Iterator, Optional

import httpx

from splox._models import SSEEvent
from splox.exceptions import (
    SploxAPIError,
    SploxAuthError,
    SploxConnectionError,
    SploxForbiddenError,
    SploxGoneError,
    SploxNotFoundError,
    SploxRateLimitError,
)

DEFAULT_BASE_URL = "https://app.splox.io/api/v1"
DEFAULT_TIMEOUT = 30.0


def _build_headers(api_key: Optional[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _raise_for_status(response: httpx.Response) -> None:
    """Raise a typed exception for non-2xx responses."""
    if response.is_success:
        return

    body = response.text
    try:
        data = response.json()
        message = data.get("error", body)
    except Exception:
        message = body

    status = response.status_code

    if status == 401:
        raise SploxAuthError(message=message, response_body=body)
    if status == 403:
        raise SploxForbiddenError(message=message, response_body=body)
    if status == 404:
        raise SploxNotFoundError(message=message, response_body=body)
    if status == 410:
        raise SploxGoneError(message=message, response_body=body)
    if status == 429:
        retry_after = None
        ra_header = response.headers.get("Retry-After")
        if ra_header:
            try:
                retry_after = float(ra_header)
            except ValueError:
                pass
        raise SploxRateLimitError(
            message=message, retry_after=retry_after, response_body=body
        )

    raise SploxAPIError(message=message, status_code=status, response_body=body)


def _parse_sse_line(line: str) -> Optional[SSEEvent]:
    """Parse a single SSE data line into an SSEEvent."""
    line = line.strip()
    if not line:
        return None
    if not line.startswith("data:"):
        return None

    payload = line[5:].strip()

    if payload == "keepalive":
        return SSEEvent(is_keepalive=True, raw_data=payload)

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return SSEEvent(raw_data=payload)

    return SSEEvent.from_dict(data)


class SyncTransport:
    """Synchronous HTTP transport using httpx."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        try:
            response = self._client.request(
                method,
                path,
                json=json_body,
                params=params,
                headers=headers,
            )
        except httpx.ConnectError as e:
            raise SploxConnectionError(f"Failed to connect to {self._base_url}: {e}") from e

        _raise_for_status(response)

        if not response.content:
            return {}
        return response.json()  # type: ignore[no-any-return]

    def stream_sse(self, path: str, *, headers: Optional[Dict[str, str]] = None) -> Iterator[SSEEvent]:
        """Open an SSE stream and yield parsed events."""
        try:
            with self._client.stream(
                "GET",
                path,
                headers={**(headers or {}), "Accept": "text/event-stream"},
                timeout=httpx.Timeout(timeout=None),  # SSE streams are long-lived
            ) as response:
                _raise_for_status(response)
                for line in response.iter_lines():
                    event = _parse_sse_line(line)
                    if event is not None:
                        yield event
        except httpx.ConnectError as e:
            raise SploxConnectionError(f"Failed to connect to SSE stream: {e}") from e

    def close(self) -> None:
        self._client.close()


class AsyncTransport:
    """Asynchronous HTTP transport using httpx."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                path,
                json=json_body,
                params=params,
                headers=headers,
            )
        except httpx.ConnectError as e:
            raise SploxConnectionError(f"Failed to connect to {self._base_url}: {e}") from e

        _raise_for_status(response)

        if not response.content:
            return {}
        return response.json()  # type: ignore[no-any-return]

    async def stream_sse(
        self, path: str, *, headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[SSEEvent]:
        """Open an SSE stream and yield parsed events asynchronously."""
        try:
            async with self._client.stream(
                "GET",
                path,
                headers={**(headers or {}), "Accept": "text/event-stream"},
                timeout=httpx.Timeout(timeout=None),
            ) as response:
                _raise_for_status(response)
                async for line in response.aiter_lines():
                    event = _parse_sse_line(line)
                    if event is not None:
                        yield event
        except httpx.ConnectError as e:
            raise SploxConnectionError(f"Failed to connect to SSE stream: {e}") from e

    async def close(self) -> None:
        await self._client.aclose()
