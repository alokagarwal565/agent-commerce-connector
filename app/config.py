"""Application configuration loaded from environment variables."""

from __future__ import annotations

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """WooCommerce connector settings.

    All secrets use ``SecretStr`` so they never leak into logs or repr.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    woocommerce_store_url: str
    woocommerce_consumer_key: SecretStr
    woocommerce_consumer_secret: SecretStr

    request_timeout_seconds: int = 15
    max_retries: int = 3
    max_per_page: int = 100

    @field_validator("woocommerce_store_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("max_retries")
    @classmethod
    def _retries_bound(cls, v: int) -> int:
        if v < 0:
            raise ValueError("max_retries must be >= 0")
        return v

    @field_validator("max_per_page")
    @classmethod
    def _per_page_bound(cls, v: int) -> int:
        if not 1 <= v <= 100:
            raise ValueError("max_per_page must be between 1 and 100")
        return v
