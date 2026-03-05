"""Tests for retry handler"""

import pytest
import asyncio
from unittest.mock import AsyncMock

import httpx

from src.utils.retry import SmartRetryHandler, ErrorType, RetryableError


class TestSmartRetryHandler:
    def test_classify_rate_limit(self):
        response = httpx.Response(429, headers={"Retry-After": "5"})
        error = httpx.HTTPStatusError("Rate limit", request=None, response=response)

        error_type, retry_after = SmartRetryHandler.classify_error(error)

        assert error_type == ErrorType.RATE_LIMIT
        assert retry_after == 5.0

    def test_classify_auth_error(self):
        response = httpx.Response(401)
        error = httpx.HTTPStatusError("Unauthorized", request=None, response=response)

        error_type, _ = SmartRetryHandler.classify_error(error)

        assert error_type == ErrorType.AUTH_ERROR

    def test_classify_server_error(self):
        response = httpx.Response(500)
        error = httpx.HTTPStatusError("Server error", request=None, response=response)

        error_type, _ = SmartRetryHandler.classify_error(error)

        assert error_type == ErrorType.SERVER_ERROR

    def test_classify_network_error(self):
        error = httpx.ConnectError("Connection failed")

        error_type, _ = SmartRetryHandler.classify_error(error)

        assert error_type == ErrorType.NETWORK

    def test_classify_timeout(self):
        error = asyncio.TimeoutError()

        error_type, _ = SmartRetryHandler.classify_error(error)

        assert error_type == ErrorType.TIMEOUT

    def test_should_retry_network(self):
        handler = SmartRetryHandler()
        assert handler.should_retry(ErrorType.NETWORK, 0)
        assert handler.should_retry(ErrorType.NETWORK, 1)
        assert not handler.should_retry(ErrorType.NETWORK, 3)

    def test_should_not_retry_auth(self):
        handler = SmartRetryHandler()
        assert not handler.should_retry(ErrorType.AUTH_ERROR, 0)

    def test_calculate_delay(self):
        handler = SmartRetryHandler(base_delay=1.0)

        # With retry_after header
        assert handler.calculate_delay(ErrorType.RATE_LIMIT, 0, 5.0) == 5.0

        # Exponential backoff
        assert handler.calculate_delay(ErrorType.NETWORK, 0, None) == 1.0
        assert handler.calculate_delay(ErrorType.NETWORK, 1, None) == 2.0
        assert handler.calculate_delay(ErrorType.NETWORK, 2, None) == 4.0

    @pytest.mark.asyncio
    async def test_execute_success(self):
        handler = SmartRetryHandler()

        async def success_func():
            return "success"

        result = await handler.execute(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self):
        handler = SmartRetryHandler(base_delay=0.01)

        call_count = 0

        async def retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection failed")
            return "success"

        result = await handler.execute(retry_func)
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_auth_error_no_retry(self):
        handler = SmartRetryHandler()

        call_count = 0

        async def auth_error_func():
            nonlocal call_count
            call_count += 1
            response = httpx.Response(401)
            raise httpx.HTTPStatusError("Unauthorized", request=None, response=response)

        with pytest.raises(RetryableError) as exc_info:
            await handler.execute(auth_error_func)

        assert exc_info.value.error_type == ErrorType.AUTH_ERROR
        assert call_count == 1  # No retry
