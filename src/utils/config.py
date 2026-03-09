"""Configuration management for PAVUI"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager"""

    _instance: "Config | None" = None
    _config: dict = {}

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """Load configuration from files and environment"""
        # __file__ = src/utils/config.py -> parent.parent.parent = pavui/
        base_dir = Path(__file__).parent.parent.parent

        # Load .env file
        env_path = base_dir / ".env"
        load_dotenv(env_path)

        # Load settings.yaml
        config_path = base_dir / "config" / "settings.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key

        Example: config.get("llm.providers.deepseek.model")
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    def get_env(self, key: str, default: str = "") -> str:
        """Get environment variable"""
        return os.getenv(key, default)

    @property
    def language(self) -> str:
        """Get UI language"""
        return self.get("language", "zh")

    @property
    def theme(self) -> str:
        """Get UI theme"""
        return self.get("ui.theme", "dark")

    @property
    def projects_dir(self) -> Path:
        """Get projects storage directory"""
        path_str = self.get("storage.projects_dir", "~/pavui_projects")
        return Path(path_str).expanduser()

    @property
    def deepseek_api_key(self) -> str:
        """Get DeepSeek API key"""
        # Environment variable takes precedence
        env_key = self.get_env("DEEPSEEK_API_KEY")
        if env_key:
            return env_key
        return self.get("llm.providers.deepseek.api_key", "")

    @property
    def deepseek_base_url(self) -> str:
        """Get DeepSeek base URL"""
        return self.get("llm.providers.deepseek.base_url", "https://api.deepseek.com/v1")

    @property
    def deepseek_model(self) -> str:
        """Get DeepSeek model"""
        return self.get("llm.providers.deepseek.model", "deepseek-chat")

    @property
    def jimeng_access_key(self) -> str:
        """Get Jimeng (Volcengine) Access Key"""
        env_key = self.get_env("JIMENG_ACCESS_KEY") or self.get_env("VOLC_ACCESSKEY")
        if env_key:
            return env_key
        return self.get("image.providers.jimeng.access_key", "")

    @property
    def jimeng_secret_key(self) -> str:
        """Get Jimeng (Volcengine) Secret Key"""
        env_key = self.get_env("JIMENG_SECRET_KEY") or self.get_env("VOLC_SECRETKEY")
        if env_key:
            return env_key
        return self.get("image.providers.jimeng.secret_key", "")

    @property
    def jimeng_model(self) -> str:
        """Get Jimeng model"""
        return self.get("image.providers.jimeng.model", "jimeng_t2i_v40")

    def reload(self) -> None:
        """Reload configuration"""
        self._load()


# Global config instance
config = Config()
