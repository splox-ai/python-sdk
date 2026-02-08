"""Splox API exception classes."""

from __future__ import annotations


class SploxError(Exception):
    """Base exception for all Splox SDK errors."""


class SploxAPIError(SploxError):
    """Raised when the Splox API returns an error response."""

    def __init__(self, message: str, status_code: int, response_body: str | None = None) -> None:
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"[{status_code}] {message}")


class SploxAuthError(SploxAPIError):
    """Raised on 401 Unauthorized responses."""

    def __init__(self, message: str = "Authentication failed", response_body: str | None = None) -> None:
        super().__init__(message=message, status_code=401, response_body=response_body)


class SploxForbiddenError(SploxAPIError):
    """Raised on 403 Forbidden responses."""

    def __init__(self, message: str = "Forbidden", response_body: str | None = None) -> None:
        super().__init__(message=message, status_code=403, response_body=response_body)


class SploxNotFoundError(SploxAPIError):
    """Raised on 404 Not Found responses."""

    def __init__(self, message: str = "Resource not found", response_body: str | None = None) -> None:
        super().__init__(message=message, status_code=404, response_body=response_body)


class SploxRateLimitError(SploxAPIError):
    """Raised on 429 Too Many Requests responses."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
        response_body: str | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message=message, status_code=429, response_body=response_body)


class SploxGoneError(SploxAPIError):
    """Raised on 410 Gone responses (e.g., expired webhook)."""

    def __init__(self, message: str = "Resource expired", response_body: str | None = None) -> None:
        super().__init__(message=message, status_code=410, response_body=response_body)


class SploxTimeoutError(SploxError):
    """Raised when an operation times out (e.g., run_and_wait)."""


class SploxConnectionError(SploxError):
    """Raised when a connection to the API cannot be established."""


class SploxStreamError(SploxError):
    """Raised when an SSE stream encounters an error."""
