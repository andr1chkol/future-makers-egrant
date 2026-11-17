from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DocumentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCUMENT_", env_file=".env", extra="ignore")
    max_bytes: int = Field(default=20 * 1024 * 1024, ge=1, le=20 * 1024 * 1024)
    max_batch_files: int = Field(default=20, ge=1, le=100)
    max_batch_bytes: int = Field(default=40 * 1024 * 1024, ge=1, le=100 * 1024 * 1024)
    max_pages: int = Field(default=100, ge=1, le=1000)
    max_rows: int = Field(default=10000, ge=1, le=100000)
    max_columns: int = Field(default=256, ge=1, le=16384)
    max_cells: int = Field(default=100000, ge=1, le=1000000)
    max_sheets: int = Field(default=50, ge=1, le=200)
    max_zip_files: int = Field(default=2000, ge=1)
    max_uncompressed_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    max_compression_ratio: int = Field(default=100, ge=1)
    max_pixels: int = Field(default=25000000, ge=1)
    max_text_chars: int = Field(default=2000000, ge=1)
    processing_seconds: float = Field(default=40, ge=1, le=45)
    validation_seconds: float = Field(default=10, ge=1, le=15)
    ocr_provider: Literal["disabled", "tesseract"] = "disabled"
    ocr_executable: Path | None = None
    ocr_languages: str = Field(default="slk+eng", pattern=r"^[a-z]{3}(\+[a-z]{3})*$")
    ocr_seconds: float = Field(default=10, ge=0.1, le=10)
