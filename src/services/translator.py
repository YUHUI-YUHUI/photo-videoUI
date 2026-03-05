"""Translation service for prompt translation"""

from .llm_service import LLMService


class Translator:
    """Translate text between languages using LLM"""

    TRANSLATE_SYSTEM_PROMPT = """你是一个专业的翻译助手。将用户提供的中文文本翻译成英文。

要求：
1. 保持原文的含义和语气
2. 翻译要自然流畅，适合AI图像生成使用
3. 保留专有名词和特定描述
4. 只输出翻译结果，不要添加任何解释

如果输入已经是英文，直接返回原文。"""

    BATCH_TRANSLATE_SYSTEM_PROMPT = """你是一个专业的翻译助手。将用户提供的中文文本列表翻译成英文。

要求：
1. 保持原文的含义和语气
2. 翻译要自然流畅，适合AI图像生成使用
3. 保留专有名词和特定描述
4. 输出JSON格式：{"translations": ["翻译1", "翻译2", ...]}
5. 保持顺序与输入一致

如果某项已经是英文，直接保留原文。"""

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def translate_to_english(self, text: str) -> str:
        """Translate Chinese text to English"""
        if not text or not text.strip():
            return text

        # Check if already English (simple heuristic)
        if self._is_english(text):
            return text

        response = await self.llm.generate(
            prompt=text,
            system_prompt=self.TRANSLATE_SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=1024,
        )

        return response.content.strip()

    async def translate_batch(self, texts: list[str]) -> list[str]:
        """Translate multiple texts at once"""
        if not texts:
            return []

        # Filter out empty texts and already English texts
        to_translate = []
        indices = []
        results = [""] * len(texts)

        for i, text in enumerate(texts):
            if not text or not text.strip():
                results[i] = text
            elif self._is_english(text):
                results[i] = text
            else:
                to_translate.append(text)
                indices.append(i)

        if not to_translate:
            return results

        # Translate in batch
        prompt = "请翻译以下文本列表：\n\n" + "\n---\n".join(
            f"{i+1}. {text}" for i, text in enumerate(to_translate)
        )

        try:
            data = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=self.BATCH_TRANSLATE_SYSTEM_PROMPT,
                temperature=0.3,
            )

            translations = data.get("translations", [])

            for i, idx in enumerate(indices):
                if i < len(translations):
                    results[idx] = translations[i]
                else:
                    results[idx] = to_translate[i]

        except Exception:
            # Fallback: translate one by one
            for i, idx in enumerate(indices):
                try:
                    results[idx] = await self.translate_to_english(to_translate[i])
                except Exception:
                    results[idx] = to_translate[i]

        return results

    @staticmethod
    def _is_english(text: str) -> bool:
        """Simple check if text is primarily English"""
        if not text:
            return True

        # Count non-ASCII characters
        non_ascii = sum(1 for c in text if ord(c) > 127)
        total = len(text.replace(" ", ""))

        if total == 0:
            return True

        # If more than 20% non-ASCII, likely not English
        return (non_ascii / total) < 0.2
