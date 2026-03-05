"""Smart retry handler for API calls"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, TypeVar

import httpx


class ErrorType(Enum):
    """Classification of errors for retry decisions"""
    NETWORK = "network"          # Network errors - retry with backoff
    RATE_LIMIT = "rate_limit"    # 429 Too Many Requests - wait and retry
    SERVER_ERROR = "server"      # 5xx errors - retry
    AUTH_ERROR = "auth"          # 401/403 - don't retry
    CLIENT_ERROR = "client"      # 4xx (except 429) - don't retry
    CONTENT_FILTER = "content"   # Content moderation - don't retry
    TIMEOUT = "timeout"          # Timeout - retry
    UNKNOWN = "unknown"          # Unknown - retry once


@dataclass
class RetryableError(Exception):
    """Error with retry information"""
    message: str
    error_type: ErrorType
    retry_after: float | None = None  # Seconds to wait before retry
    original_error: Exception | None = None

    def __str__(self) -> str:
        return self.message


T = TypeVar("T")


class SmartRetryHandler:
    """Intelligent retry handler based on error type"""

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BASE_DELAY = 1.0  # seconds
    DEFAULT_MAX_DELAY = 30.0  # seconds

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    @staticmethod
    def classify_error(error: Exception) -> tuple[ErrorType, float | None]:
        """Classify an error and determine retry strategy

        Returns: (error_type, retry_after_seconds)
        """
        # HTTP errors from httpx
        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code

            if status == 429:
                # Check Retry-After header
                retry_after = error.response.headers.get("Retry-After")
                wait_time = float(retry_after) if retry_after else 5.0
                return ErrorType.RATE_LIMIT, wait_time

            if status in (401, 403):
                return ErrorType.AUTH_ERROR, None

            if 400 <= status < 500:
                return ErrorType.CLIENT_ERROR, None

            if status >= 500:
                return ErrorType.SERVER_ERROR, None

        # Network errors
        if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout)):
            return ErrorType.NETWORK, None

        # Timeout errors
        if isinstance(error, (httpx.TimeoutException, asyncio.TimeoutError)):
            return ErrorType.TIMEOUT, None

        # Content filter (check message)
        error_msg = str(error).lower()
        if any(kw in error_msg for kw in ["content_filter", "content_policy", "moderation"]):
            return ErrorType.CONTENT_FILTER, None

        return ErrorType.UNKNOWN, None

    def should_retry(self, error_type: ErrorType, attempt: int) -> bool:
        """Determine if we should retry based on error type and attempt count"""
        if attempt >= self.max_retries:
            return False

        # These error types should not be retried
        if error_type in (ErrorType.AUTH_ERROR, ErrorType.CLIENT_ERROR, ErrorType.CONTENT_FILTER):
            return False

        return True

    def calculate_delay(self, error_type: ErrorType, attempt: int, retry_after: float | None) -> float:
        """Calculate delay before next retry"""
        # Use Retry-After header if available
        if retry_after is not None:
            return min(retry_after, self.max_delay)

        # Exponential backoff: base_delay * 2^attempt
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        on_retry: Callable[[int, Exception, float], None] | None = None,
        **kwargs,
    ) -> T:
        """Execute function with smart retry

        Args:
            func: Async function to execute
            *args: Function arguments
            on_retry: Callback when retrying (attempt, error, delay)
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            RetryableError: When all retries exhausted or non-retryable error
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                last_error = e
                error_type, retry_after = self.classify_error(e)

                if not self.should_retry(error_type, attempt):
                    raise RetryableError(
                        message=str(e),
                        error_type=error_type,
                        original_error=e,
                    )

                delay = self.calculate_delay(error_type, attempt, retry_after)

                if on_retry:
                    on_retry(attempt + 1, e, delay)

                await asyncio.sleep(delay)

        # All retries exhausted
        raise RetryableError(
            message=f"Max retries ({self.max_retries}) exceeded. Last error: {last_error}",
            error_type=ErrorType.UNKNOWN,
            original_error=last_error,
        )
