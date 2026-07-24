"""
ARIA Configuration - Pydantic Settings for all services.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "ARIA"
    app_env: str = "development"
    secret_key: str = "change-this-in-production"
    debug: bool = True

    # --- Database ---
    # Defaults to local SQLite; override with DATABASE_URL env var for PostgreSQL
    database_url: str = "sqlite+aiosqlite:///./sqlite.db"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- ChromaDB ---
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # --- Ollama ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"

    # --- MinIO ---
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "aria_minio"
    minio_root_password: str = "aria_minio_secret"
    minio_bucket: str = "aria-documents"
    minio_use_ssl: bool = False

    # --- JWT ---
    jwt_secret_key: str = "change-this-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # --- Obsidian ---
    obsidian_vault_path: Optional[str] = None
    obsidian_sync_interval: int = 300  # seconds

    # --- Overleaf Integration ---
    overleaf_browser: str = "chrome"       # 'chrome' or 'firefox' — browser where user is logged into Overleaf
    overleaf_enabled: bool = True          # Set to False to disable Overleaf push globally

    # --- News ---
    news_api_key: Optional[str] = None
    arxiv_max_results: int = 20

    # --- Paths ---
    upload_dir: str = "./uploads"
    reports_dir: str = "./reports"

    # --- Document Processing ---
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_file_size_mb: int = 100
    ocr_enabled: bool = True
    ocr_languages: str = "en"

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"

    class Config:
        env_file = (".env", "../.env")
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
