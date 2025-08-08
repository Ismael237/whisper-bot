"""Service layer package for WhisperBot.

This package contains application service modules such as `user_service`
and `session_service` which encapsulate business logic and integrations
with persistence layers (PostgreSQL via SQLAlchemy and Redis).
"""

__all__ = [
    "user_service",
    "session_service",
]


