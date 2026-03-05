"""Tests for LLM adapters"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.adapters import DeepSeekAdapter, LLMResponse


class TestDeepSeekAdapter:
    def test_init(self):
        adapter = DeepSeekAdapter(api_key="test-key")
        assert adapter.api_key == "test-key"
        assert adapter.base_url == DeepSeekAdapter.DEFAULT_BASE_URL
        assert adapter.model == DeepSeekAdapter.DEFAULT_MODEL

    def test_init_custom(self):
        adapter = DeepSeekAdapter(
            api_key="test-key",
            base_url="https://custom.api.com",
            model="deepseek-coder",
        )
        assert adapter.base_url == "https://custom.api.com"
        assert adapter.model == "deepseek-coder"

    def test_available_models(self):
        adapter = DeepSeekAdapter(api_key="test-key")
        models = adapter.get_available_models()
        assert "deepseek-chat" in models
        assert "deepseek-coder" in models

    @pytest.mark.asyncio
    async def test_generate_success(self):
        adapter = DeepSeekAdapter(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"total_tokens": 10},
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            response = await adapter.generate("Say hello")

            assert response.content == "Hello!"
            assert response.success

    @pytest.mark.asyncio
    async def test_generate_json_success(self):
        adapter = DeepSeekAdapter(api_key="test-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"key": "value"}'}}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await adapter.generate_json("Generate JSON")

            assert result == {"key": "value"}


class TestLLMResponse:
    def test_success(self):
        response = LLMResponse(content="Hello", model="test")
        assert response.success

    def test_empty_content(self):
        response = LLMResponse(content="", model="test")
        assert not response.success
