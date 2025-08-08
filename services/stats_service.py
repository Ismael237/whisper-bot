from __future__ import annotations

from typing import Optional, Dict, Any

from sqlalchemy.orm import Session as OrmSession
from sqlalchemy import func

from database.database import get_db_session
from database.models import User, AnonymousMessage, GlobalStats
from utils.logger import logger


def get_user_stats(telegram_id: int, *, session: Optional[OrmSession] = None) -> Dict[str, Any]:
    """Return per-user stats summary.

    Includes: username, is_active, created_at, last_activity,
    total_messages_received, total_messages_sent, unread_count.
    """

    def _op(db: OrmSession) -> Dict[str, Any]:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return {
                "exists": False,
                "message": "User not found",
            }
        unread = (
            db.query(func.count(AnonymousMessage.id))
            .filter(
                AnonymousMessage.recipient_id == user.id,
                AnonymousMessage.is_read.is_(False),
            )
            .scalar()
            or 0
        )
        return {
            "exists": True,
            "username": user.username,
            "is_active": bool(user.is_active),
            "created_at": user.created_at,
            "last_activity": user.last_activity,
            "total_messages_received": int(user.total_messages_received or 0),
            "total_messages_sent": int(user.total_messages_sent or 0),
            "unread_count": int(unread),
        }

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def get_global_stats(*, session: Optional[OrmSession] = None) -> Dict[str, Any]:
    """Return global stats for today, updating aggregates if necessary."""

    def _op(db: OrmSession) -> Dict[str, Any]:
        try:
            stats = GlobalStats.get_or_create_today(db)
            # Refresh aggregates best-effort
            try:
                stats.update_from_query(db)
            except Exception as agg_ex:
                logger.warning(f"[StatsService] Failed to refresh aggregates: {agg_ex}")
            db.flush()
            return stats.to_dict()
        except Exception as e:
            logger.error(f"[StatsService] get_global_stats error: {e}")
            return {
                "date": None,
                "total_users": 0,
                "active_users": 0,
                "messages_sent_today": 0,
                "new_registrations": 0,
            }

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


