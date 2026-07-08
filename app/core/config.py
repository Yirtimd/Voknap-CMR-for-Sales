from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CMR Sales App"
    database_url: str = "postgresql+psycopg://cmr:cmr@localhost:5432/cmr"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 1440
    openai_api_key: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "gml-5"
    embedding_provider: str = "local"
    embedding_model: str = "text-embedding-3-small"
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 180

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
