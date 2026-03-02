from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_TYPE: Literal["sqlite", "mongo"] = "sqlite"
    SQLITE_URL: str = "sqlite:///./app.db"
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "obsidian-webdev"

    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    ENCRYPTION_KEY: str = ""

    FERNET_MASTER_KEY: str = ""

    RATE_LIMIT_USER: int = 60
    RATE_LIMIT_API_CLIENT: int = 100

    CORS_ORIGINS: list[str] = ["*"]

    PROJECTS_DATA_DIR: str = "./data/projects"

    DOCKER_SOCKET: str = ""
    CONTAINER_IDLE_TIMEOUT_MINUTES: int = 30
    CONTAINER_HARD_REMOVE_HOURS: int = 48
    HOST_PROJECTS_DIR: str = ""

    QDRANT_URL: str = "http://localhost:6333"

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LMSTUDIO_BASE_URL: str = "http://localhost:1234/v1"

    TAVILY_API_KEY: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
