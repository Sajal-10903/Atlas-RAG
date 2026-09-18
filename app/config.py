from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "Atlas RAG"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://atlas:atlas@localhost:5432/atlas"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "atlas_chunks"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    embedding_provider: str = "openai"
    max_upload_mb: int = 25
    upload_dir: str = "data/uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
