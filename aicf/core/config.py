"""
AICF Configuration System

Centralized configuration management for the AI Content Factory.
Supports environment variables, default values, and validation.
"""

from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "AICF - AI Content Factory"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Database
    DATABASE_URL: str = "postgresql://aicf:aicf_password@localhost:5432/aicf_db"
    DB_ECHO: bool = False  # Log SQL queries
    
    # AI Provider
    AI_PROVIDER: str = "openai"  # openai, anthropic, ollama, etc.
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "gpt-4o-mini"
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.7
    
    # Storage
    STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 500
    
    # Workflow
    MAX_CONCURRENT_WORKFLOWS: int = 5
    WORKFLOW_TIMEOUT_MINUTES: int = 60
    
    # Memory
    MEMORY_ENABLED: bool = True
    MEMORY_RETENTION_DAYS: int = 90
    
    # API
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()
