from __future__ import annotations

from typing import Dict

from telegram import Update
from telegram.ext import ContextTypes

from services.session_service import (
    get_active_sessions,
    refresh_session_ttl,
)
from database.models import SessionType
from utils.logger import logger


async def session_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pre-processing middleware to load and refresh user sessions.

    - Loads all active sessions for the user into context.user_data['sessions'] keyed by type
    - Refreshes TTL for SETUP session as a baseline (others optionally later)
    - Safe no-op for updates without a user
    """
    try:
        tg_user = update.effective_user if hasattr(update, "effective_user") else None
        if not tg_user:
            return

        # Load all active sessions
        sessions = get_active_sessions(tg_user.id)
        by_type: Dict[str, object] = {}
        for s in sessions:
            by_type[str(s.session_type.value)] = s
        context.user_data["sessions"] = by_type

        # Refresh baseline SETUP TTL if present
        try:
            refresh_session_ttl(tg_user.id, SessionType.SETUP)
        except Exception:
            # Non-fatal
            pass

    except Exception as e:
        logger.warning(f"[Middleware] session_middleware error: {e}")


