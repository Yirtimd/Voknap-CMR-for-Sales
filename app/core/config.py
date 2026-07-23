from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CRM Sales App"
    database_url: str = "postgresql+psycopg://cmr:cmr@localhost:5432/cmr"
    database_runtime_role: str = "cmr_app"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 1440
    dev_user_password: str | None = None
    openai_api_key: str | None = None
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str = "glm-5.2"
    embedding_provider: str = "local"
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_version: str = "1"
    embedding_dimensions: int = 1536
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 180
    knowledge_upload_dir: str = "data/knowledge_uploads"
    knowledge_max_upload_bytes: int = 20_000_000
    knowledge_max_pdf_pages: int = 500
    knowledge_max_extracted_chars: int = 500_000
    knowledge_storage_backend: str = "local"
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str = "cmr-knowledge"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = True
    s3_server_side_encryption: str | None = None
    knowledge_ocr_enabled: bool = True
    knowledge_ocr_languages: str = "rus+eng"
    knowledge_ocr_dpi: int = 200
    knowledge_ocr_max_pages: int = 50
    knowledge_ocr_page_timeout_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
