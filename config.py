import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path, override=True)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
BOT_USERNAME = os.getenv("BOT_USERNAME", "WhisperBot")

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Application Settings
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes", "on")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()

# Limits
MAX_MESSAGE_LENGTH = os.getenv("MAX_MESSAGE_LENGTH", 1000)
MIN_USERNAME_LENGTH = os.getenv("MIN_USERNAME_LENGTH", 3)
MAX_USERNAME_LENGTH = os.getenv("MAX_USERNAME_LENGTH", 20)
SESSION_TIMEOUT_HOURS = os.getenv("SESSION_TIMEOUT_HOURS", 1)

# Rate Limiting
RATE_LIMIT_MESSAGES_PER_HOUR = os.getenv("RATE_LIMIT_MESSAGES_PER_HOUR", 10)
ENABLE_FLOOD_PROTECTION = os.getenv("ENABLE_FLOOD_PROTECTION", "True").lower() in ("true", "1", "yes", "on")

# Analytics
ENABLE_ANALYTICS = os.getenv("ENABLE_ANALYTICS", "True").lower() in ("true", "1", "yes", "on")
CLEANUP_OLD_SESSIONS_HOURS = os.getenv("CLEANUP_OLD_SESSIONS_HOURS", 24)

# Database Pooling
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 10))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 1800))  # seconds