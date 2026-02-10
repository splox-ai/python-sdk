"""Tests for exception classes."""

from splox.exceptions import (
    SploxAPIError,
    SploxAuthError,
    SploxConnectionError,
    SploxError,
    SploxForbiddenError,
    SploxGoneError,
    SploxNotFoundError,
    SploxRateLimitError,
    SploxStreamError,
    SploxTimeoutError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_splox_error(self) -> None:
        assert issubclass(SploxAPIError, SploxError)
        assert issubclass(SploxAuthError, SploxAPIError)
        assert issubclass(SploxForbiddenError, SploxAPIError)
        assert issubclass(SploxNotFoundError, SploxAPIError)
        assert issubclass(SploxRateLimitError, SploxAPIError)
        assert issubclass(SploxGoneError, SploxAPIError)
        assert issubclass(SploxTimeoutError, SploxError)
        assert issubclass(SploxConnectionError, SploxError)
        assert issubclass(SploxStreamError, SploxError)

    def test_api_error_has_status_code(self) -> None:
        e = SploxAPIError(message="bad", status_code=400)
        assert e.status_code == 400
        assert e.message == "bad"
        assert "[400]" in str(e)

    def test_auth_error_defaults(self) -> None:
        e = SploxAuthError()
        assert e.status_code == 401
        assert "Authentication failed" in str(e)

    def test_rate_limit_retry_after(self) -> None:
        e = SploxRateLimitError(retry_after=30.0)
        assert e.retry_after == 30.0
        assert e.status_code == 429
