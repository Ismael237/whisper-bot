from __future__ import annotations

from typing import Callable, Awaitable, Any

from telegram import Update
from telegram.ext import ContextTypes

from services.session_service import get_active_session
from database.models import SessionType


def require_session_step(session_type: SessionType, step: str) -> Callable[[Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]], Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]]:
    """Decorator for handlers to require a specific session step.

    If the condition is not met, the wrapped handler is skipped (returns early).
    """

    def decorator(func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            tg_user = update.effective_user if hasattr(update, "effective_user") else None
            if not tg_user:
                return
            sess = get_active_session(tg_user.id, session_type)
            if not sess or (sess.current_step or "") != step:
                return
            return await func(update, context)

        return wrapper

    return decorator


async def advance_step(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    session_type: SessionType,
    next_step: str | None,
) -> None:
    """Advance the current_step of a user's session to the next step (or clear)."""
    from services.session_service import set_current_step

    tg_user = update.effective_user if hasattr(update, "effective_user") else None
    if not tg_user:
        return
    set_current_step(tg_user.id, session_type, next_step)


