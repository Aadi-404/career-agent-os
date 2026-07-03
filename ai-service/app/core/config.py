from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    llm_mode: Literal["mock", "live"] = "mock"
    llm_provider: Literal["openai", "gemini", "groq"] = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    google_api_key: str = ""
    llm_timeout_seconds: int = Field(default=45, ge=5, le=120)
    embedding_provider: Literal["auto", "gemini", "openai", "local"] = "auto"
    embedding_model: str = ""
    embedding_timeout_seconds: int = Field(default=20, ge=3, le=60)
    embedding_fallback_local: bool = True
    jd_parser_mode: Literal["deterministic", "llm", "auto"] = "deterministic"
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    environment: Literal["development", "staging", "production"] = "development"
    require_user_auth: bool = False
    admin_user_ids: str = "local-aditya"
    billing_webhook_secret: str = ""
    billing_checkout_provider: Literal["manual", "stripe", "razorpay", "paddle"] = "manual"
    billing_checkout_url: str = ""
    billing_checkout_success_url: str = ""
    billing_checkout_cancel_url: str = ""
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}")
        return normalized

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
