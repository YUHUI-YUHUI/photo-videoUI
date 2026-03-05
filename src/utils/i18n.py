"""Internationalization support for PAVUI"""

import json
from pathlib import Path
from typing import Any


class I18n:
    """Internationalization manager"""

    _instance: "I18n | None" = None
    _translations: dict = {}
    _language: str = "zh"

    def __new__(cls) -> "I18n":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all()
        return cls._instance

    def _load_all(self) -> None:
        """Load all translation files"""
        # __file__ = src/utils/i18n.py -> parent.parent.parent = pavui/
        locales_dir = Path(__file__).parent.parent.parent / "locales"

        for lang_file in locales_dir.glob("*.json"):
            lang_code = lang_file.stem
            with open(lang_file, "r", encoding="utf-8") as f:
                self._translations[lang_code] = json.load(f)

    def set_language(self, language: str) -> None:
        """Set current language"""
        if language in self._translations:
            self._language = language
        else:
            raise ValueError(f"Language '{language}' not supported. Available: {list(self._translations.keys())}")

    @property
    def language(self) -> str:
        """Get current language"""
        return self._language

    @property
    def available_languages(self) -> list[str]:
        """Get list of available languages"""
        return list(self._translations.keys())

    def get(self, key: str, **kwargs) -> str:
        """Get translation by dot-separated key

        Example: i18n.get("script.generate")

        Supports string formatting with kwargs:
        Example: i18n.get("errors.generation_failed", error="timeout")
        """
        keys = key.split(".")
        value: Any = self._translations.get(self._language, {})

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return key  # Return key if not found

            if value is None:
                return key

        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except KeyError:
                return value

        return value if isinstance(value, str) else key

    def __call__(self, key: str, **kwargs) -> str:
        """Shorthand for get()"""
        return self.get(key, **kwargs)


# Global i18n instance
i18n = I18n()


def t(key: str, **kwargs) -> str:
    """Shorthand translation function"""
    return i18n.get(key, **kwargs)
