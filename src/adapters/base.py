"""Base LLM adapter interface"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    raw_response: Any = None

    @property
    def success(self) -> bool:
        return bool(self.content)


class BaseLLMAdapter(ABC):
    """Base class for LLM adapters"""

    name: str = "base"
    display_name: str = "Base Adapter"

    def __init__(self, api_key: str, base_url: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Generate text from prompt"""
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict:
        """Generate JSON response"""
        pass

    @abstractmethod
    def get_available_models(self) -> list[str]:
        """Get list of available models"""
        pass

    async def test_connection(self) -> bool:
        """Test if the adapter is properly configured"""
        try:
            response = await self.generate("Say 'ok'", max_tokens=10)
            return response.success
        except Exception:
            return False
