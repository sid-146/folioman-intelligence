"""Configuration and environment settings for Folioman Intelligence."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FoliomanSettings(BaseSettings):
    """Folioman client configuration backed by environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="FOLIOMAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = Field(default="http://localhost:8000")
    username: str = Field(default="")
    password: str = Field(default="")
    timeout: float = Field(default=30.0)

    # Aliases to match conventional naming patterns
    @property
    def folioman_url(self) -> str:
        return self.base_url

    @property
    def folioman_username(self) -> str:
        return self.username

    @property
    def folioman_password(self) -> str:
        return self.password


settings = FoliomanSettings()
