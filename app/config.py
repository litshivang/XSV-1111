import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Application
    app_name: str = "AI Travel Agent"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    
    # Redis & Celery
    redis_url: str = Field(env="REDIS_URL")
    celery_broker_url: str = Field(env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(env="CELERY_RESULT_BACKEND")
    
    # AI Services
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-1106-preview", env="OPENAI_MODEL")
    ai_temperature: float = Field(default=0.1, env="AI_TEMPERATURE")
    
    # Email Integration - Gmail
    gmail_credentials_file: str = Field(env="GMAIL_CREDENTIALS_FILE")
    gmail_token_file: str = Field(env="GMAIL_TOKEN_FILE")
    gmail_scopes: list = ["https://www.googleapis.com/auth/gmail.readonly"]
    
    # Email Integration - Outlook
    outlook_client_id: str = Field(env="OUTLOOK_CLIENT_ID")
    outlook_client_secret: str = Field(env="OUTLOOK_CLIENT_SECRET")
    outlook_tenant_id: str = Field(env="OUTLOOK_TENANT_ID")
    
    # File Storage
    file_storage_path: str = Field(default="./storage", env="FILE_STORAGE_PATH")
    template_path: str = Field(default="./templates", env="TEMPLATE_PATH")
    
    # Email Processing
    max_emails_per_batch: int = Field(default=50, env="MAX_EMAILS_PER_BATCH")
    email_processing_timeout: int = Field(default=300, env="EMAIL_PROCESSING_TIMEOUT")
    
    # Performance
    max_workers: int = Field(default=4, env="MAX_WORKERS")
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()