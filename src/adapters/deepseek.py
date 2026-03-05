"""DeepSeek LLM adapter"""

import json
import re

import httpx

from .base import BaseLLMAdapter, LLMResponse


class DeepSeekAdapter(BaseLLMAdapter):
    """DeepSeek API adapter"""

    name = "deepseek"
    display_name = "DeepSeek"

    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"

    AVAILABLE_MODELS = [
        "deepseek-chat",
        "deepseek-coder",
    ]

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url or self.DEFAULT_BASE_URL,
            model=model or self.DEFAULT_MODEL,
        )

    def get_available_models(self) -> list[str]:
        return self.AVAILABLE_MODELS

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Generate text from prompt"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs,
                },
            )

            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]

            return LLMResponse(
                content=content,
                model=self.model,
                usage=data.get("usage", {}),
                raw_response=data,
            )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict:
        """Generate JSON response using JSON mode"""
        # Add JSON instruction to system prompt
        json_system = (system_prompt or "") + "\n\n你必须只输出有效的JSON，不要包含任何其他文字。"

        response = await self.generate(
            prompt=prompt,
            system_prompt=json_system,
            temperature=temperature,
            response_format={"type": "json_object"},
            **kwargs,
        )

        # Parse JSON from response
        content = response.content.strip()

        # Try to extract JSON if wrapped in markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if json_match:
            content = json_match.group(1).strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Try to find JSON object in content
            json_match = re.search(r"(\{[\s\S]*\})", content)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse JSON response: {e}\nContent: {content[:500]}")
