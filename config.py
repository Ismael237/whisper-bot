import os
from dotenv import load_dotenv
from pydantic import BaseSettings, PostgresDsn, validator
from typing import Optional

# Load environment variables from .env file if it exists
load_dotenv()

class Settings(BaseSettings):
    # Bot Configuration
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_ID: int
    BOT_USERNAME: str = "WhisperBot"
    
    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: Optional[str] = None
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Application Settings
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Limits
    MAX_MESSAGE_LENGTH: int = 1000
    MIN_USERNAME_LENGTH: int = 3
    MAX_USERNAME_LENGTH: int = 20
    SESSION_TIMEOUT_HOURS: int = 1
    
    # Rate Limiting
    RATE_LIMIT_MESSAGES_PER_HOUR: int = 10
    ENABLE_FLOOD_PROTECTION: bool = True
    
    # Analytics
    ENABLE_ANALYTICS: bool = True
    CLEANUP_OLD_SESSIONS_HOURS: int = 24
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return str(
            PostgresDsn.build(
                scheme="postgresql",
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("POSTGRES_SERVER"),
                path=f"/{os.getenv('POSTGRES_DB') or ''}",
            )
        )

# Create settings instance
settings = Settings()
