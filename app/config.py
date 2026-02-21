"""
NetKeeper - Configuración central con Pydantic Settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "NetKeeper"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    BASE_DOMAIN: str = "netkeeper.com.mx"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://netkeeper:netkeeper@localhost:5432/netkeeper"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Encripción MikroTik credentials
    ENCRYPTION_KEY: str = "change-this-in-production-use-fernet-key"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
