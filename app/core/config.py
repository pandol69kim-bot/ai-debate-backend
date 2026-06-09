from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "AI Arena"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Database - 환경 변수에서 읽고 asyncpg 형식으로 변환
    _raw_database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://arena:arena_pass@localhost:5432/arena_db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-secret-key-at-least-32-chars")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    ALGORITHM: str = "HS256"

    # AI API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # AI Models
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_MODEL: str = "claude-opus-4-8"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    JUDGE_MODEL: str = "gpt-4o"

    # Debate Settings
    MAX_DEBATE_ROUNDS: int = 3
    MAX_TOKENS_PER_RESPONSE: int = 3000
    DEBATE_TIMEOUT_SECONDS: int = 180

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://frontend:3000"]

    class Config:
        env_file = (".env", "../.env")
        extra = "ignore"

    @property
    def DATABASE_URL(self) -> str:
        """DATABASE_URL을 asyncpg 형식으로 변환"""
        url = self._raw_database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """동기 드라이버용 DATABASE_URL"""
        url = self._raw_database_url
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url

    @property
    def REDIS_URL(self) -> str:
        return os.getenv("REDIS_URL", "redis://localhost:6379/0")


settings = Settings()