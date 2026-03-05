"""LLM service for unified LLM access"""

from typing import Callable

from ..adapters import BaseLLMAdapter, LLMResponse
from ..utils.retry import SmartRetryHandler


class LLMService:
    """Unified LLM service with retry handling"""

    def __init__(self, adapter: BaseLLMAdapter):
        self.adapter = adapter
        self.retry_handler = SmartRetryHandler()

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        on_retry: Callable[[int, Exception, float], None] | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text with retry handling"""
        return await self.retry_handler.execute(
            self.adapter.generate,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            on_retry=on_retry,
            **kwargs,
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        on_retry: Callable[[int, Exception, float], None] | None = None,
        **kwargs,
    ) -> dict:
        """Generate JSON with retry handling"""
        return await self.retry_handler.execute(
            self.adapter.generate_json,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            on_retry=on_retry,
            **kwargs,
        )

    async def test_connection(self) -> bool:
        """Test LLM connection"""
        return await self.adapter.test_connection()
