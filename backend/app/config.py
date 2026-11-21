from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["none", "gemini", "openai", "ollama"] = "none"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    max_file_size_mb: int = 20
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider == "gemini":
            return bool(self.gemini_api_key.strip())
        if self.llm_provider == "openai":
            return bool(self.openai_api_key.strip())
        if self.llm_provider == "ollama":
            return bool(self.ollama_base_url.strip())
        return False


settings = Settings()
