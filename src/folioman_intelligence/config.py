"""Configuration and environment settings for Folioman Intelligence."""

from __future__ import annotations
from dotenv import load_dotenv

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

print(f"Env Loaded : {load_dotenv()}")


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


class LLMSettings(BaseSettings):
    """LLM configuration backed by environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MODEL_NAME: str = Field(default="gpt-4")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2048)
    api_key: SecretStr | None = None


settings = FoliomanSettings()
llm_settings = LLMSettings()
