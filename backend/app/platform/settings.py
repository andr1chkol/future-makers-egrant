from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    app_mode: Literal["live", "fixture"] = "fixture"
    database_url: SecretStr = SecretStr("postgresql+psycopg://egrant@localhost:5432/egrant")
    file_storage_path: Path = Path(".private/files")
    public_origin: str = "http://localhost:5173"
    dev_auth_bypass: bool = False
    access_code: SecretStr | None = None
    cookie_secure: bool = True
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
    ocr_base_url: str | None = None
    ocr_api_key: SecretStr | None = None
    egrant_base_url: str | None = None
    egrant_token: SecretStr | None = None

    @model_validator(mode="after")
    def validate_access(self):
        origin = urlparse(self.public_origin)
        local = origin.hostname in {"localhost", "127.0.0.1", "::1"}
        if origin.scheme not in {"http", "https"} or not origin.netloc:
            raise ValueError("PUBLIC_ORIGIN must be an HTTP origin")
        if origin.path or origin.query or origin.fragment or origin.username:
            raise ValueError("PUBLIC_ORIGIN must not contain a path or credentials")
        if not self.database_url.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use PostgreSQL with psycopg")
        if self.dev_auth_bypass and (self.app_mode != "fixture" or not local):
            raise ValueError("DEV_AUTH_BYPASS requires localhost fixture mode")
        if not self.cookie_secure and not (self.app_mode == "fixture" and local):
            raise ValueError("Insecure cookies require localhost fixture mode")
        if not self.dev_auth_bypass and (
            not self.access_code or len(self.access_code.get_secret_value()) < 24
        ):
            raise ValueError("ACCESS_CODE must have at least 24 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
