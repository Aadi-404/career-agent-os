from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_mode: Literal["mock", "live"] = "mock"
    llm_provider: Literal["openai", "gemini", "groq"] = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_timeout_seconds: int = Field(default=45, ge=5, le=120)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
