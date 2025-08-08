from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional, Dict, Any, List

import redis
from sqlalchemy.orm import Session as OrmSession

from config import REDIS_URL, SESSION_TIMEOUT_HOURS
from database.models import UserSession, SessionType
from database.database import get_db_session
from utils.helpers import get_utc_time
from utils.logger import logger


_redis_client: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    """Get a singleton Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


@dataclass
class SessionResult:
    """Result of create or fetch session operations."""
    session: UserSession
    created: bool


def _redis_key(telegram_id: int, session_type: SessionType) -> str:
    return f"session:{int(telegram_id)}:{session_type.value}"


def create_or_get_session(
    telegram_id: int,
    session_type: SessionType = SessionType.SETUP,
    *,
    initial_data: Optional[Dict[str, Any]] = None,
    expires_in_hours: Optional[float] = None,
    target_user_id: Optional[int] = None,
    session: Optional[OrmSession] = None,
) -> SessionResult:
    """Create or fetch an active session for the user, persisted in DB and Redis.

    Args:
        telegram_id: The Telegram identifier of the user
        session_type: The type/state of the session
        initial_data: Optional initial JSON data payload
        expires_in_hours: Optional TTL; defaults to `SESSION_TIMEOUT_HOURS`
        target_user_id: Optional user id associated to session
        session: Optional SQLAlchemy session; if omitted a managed session is used

    Returns:
        SessionResult containing the active session and whether it was newly created
    """

    ttl_hours = float(expires_in_hours or SESSION_TIMEOUT_HOURS or 1)

    def _op(db: OrmSession) -> SessionResult:
        now = get_utc_time()
        existing = UserSession.get_active_session(db, telegram_id, session_type)
        if existing:
            # Refresh Redis TTL and merge data
            key = _redis_key(telegram_id, session_type)
            r = _get_redis()
            try:
                if initial_data:
                    existing.update_data(initial_data, db)
                # Update Redis copy
                payload = {
                    "telegram_id": telegram_id,
                    "session_type": session_type.value,
                    "target_user_id": target_user_id or existing.target_user_id,
                    "current_step": existing.current_step,
                    "session_data": existing.session_data or {},
                    "expires_at": (now + timedelta(hours=ttl_hours)).isoformat(),
                }
                r.setex(key, int(ttl_hours * 3600), json.dumps(payload))
            except Exception as re:
                logger.warning(f"[SessionService] Redis update failed: {re}")
            db.flush()
            return SessionResult(session=existing, created=False)

        # Create new session in DB
        expires_at = now + timedelta(hours=ttl_hours)
        sess = UserSession(
            telegram_id=telegram_id,
            session_type=session_type,
            target_user_id=target_user_id,
            current_step=None,
            session_data=initial_data or {},
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        db.add(sess)
        db.flush()

        # Mirror to Redis
        key = _redis_key(telegram_id, session_type)
        r = _get_redis()
        try:
            payload = {
                "telegram_id": telegram_id,
                "session_type": session_type.value,
                "target_user_id": target_user_id,
                "current_step": None,
                "session_data": sess.session_data,
                "expires_at": expires_at.isoformat(),
            }
            r.setex(key, int(ttl_hours * 3600), json.dumps(payload))
        except Exception as re:
            logger.warning(f"[SessionService] Redis set failed: {re}")

        logger.info(f"[SessionService] Created session type={session_type.value} telegram_id={telegram_id}")
        return SessionResult(session=sess, created=True)

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def update_session_data(
    telegram_id: int,
    session_type: SessionType,
    data: Dict[str, Any],
    *,
    session: Optional[OrmSession] = None,
) -> UserSession:
    """Update the JSON data for a user's session in DB and Redis."""

    def _op(db: OrmSession) -> UserSession:
        sess = UserSession.get_active_session(db, telegram_id, session_type)
        if not sess:
            raise ValueError("Active session not found")
        sess.update_data(data, db)
        db.flush()
        # Mirror to Redis (refresh TTL)
        key = _redis_key(telegram_id, session_type)
        try:
            r = _get_redis()
            ttl_hours = float(SESSION_TIMEOUT_HOURS or 1)
            payload = {
                "telegram_id": telegram_id,
                "session_type": session_type.value,
                "target_user_id": sess.target_user_id,
                "current_step": sess.current_step,
                "session_data": sess.session_data,
                "expires_at": sess.expires_at.isoformat(),
            }
            r.setex(key, int(ttl_hours * 3600), json.dumps(payload))
        except Exception as re:
            logger.warning(f"[SessionService] Redis update failed: {re}")
        return sess

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def clear_session(
    telegram_id: int,
    session_type: SessionType,
    *,
    session: Optional[OrmSession] = None,
) -> None:
    """Expire and remove an active session from DB and Redis."""

    def _op(db: OrmSession) -> None:
        sess = UserSession.get_active_session(db, telegram_id, session_type)
        if sess:
            db.delete(sess)
            db.flush()
        key = _redis_key(telegram_id, session_type)
        try:
            _get_redis().delete(key)
        except Exception as re:
            logger.warning(f"[SessionService] Redis delete failed: {re}")

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def set_current_step(
    telegram_id: int,
    session_type: SessionType,
    step: Optional[str],
    *,
    session: Optional[OrmSession] = None,
) -> UserSession:
    """Set the current_step for the active session and mirror to Redis.

    Args:
        telegram_id: Telegram user id
        session_type: SessionType of the session to update
        step: New step string or None
        session: Optional SQLAlchemy session

    Returns:
        The updated UserSession
    """

    def _op(db: OrmSession) -> UserSession:
        sess = UserSession.get_active_session(db, telegram_id, session_type)
        if not sess:
            raise ValueError("Active session not found")
        sess.current_step = step
        sess.updated_at = get_utc_time()
        db.add(sess)
        db.flush()

        # Mirror to Redis
        key = _redis_key(telegram_id, session_type)
        try:
            r = _get_redis()
            ttl_hours = float(SESSION_TIMEOUT_HOURS or 1)
            payload = {
                "telegram_id": telegram_id,
                "session_type": session_type.value,
                "target_user_id": sess.target_user_id,
                "current_step": sess.current_step,
                "session_data": sess.session_data or {},
                "expires_at": sess.expires_at.isoformat(),
            }
            r.setex(key, int(ttl_hours * 3600), json.dumps(payload))
        except Exception as re:
            logger.warning(f"[SessionService] Redis update failed: {re}")
        return sess

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def get_active_session(
    telegram_id: int,
    session_type: Optional[SessionType] = None,
    *,
    session: Optional[OrmSession] = None,
) -> Optional[UserSession]:
    """Convenience accessor for current active session from DB.

    Args:
        telegram_id: Telegram user id
        session_type: Optional session type to filter
        session: Optional SQLAlchemy session

    Returns:
        The active UserSession or None
    """

    def _op(db: OrmSession) -> Optional[UserSession]:
        return UserSession.get_active_session(db, telegram_id, session_type)

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def get_active_sessions(
    telegram_id: int,
    *,
    session: Optional[OrmSession] = None,
) -> List[UserSession]:
    """Return all active sessions for a given user (all types).

    Args:
        telegram_id: Telegram user id
        session: Optional SQLAlchemy session

    Returns:
        List of active `UserSession` instances
    """

    def _op(db: OrmSession) -> List[UserSession]:
        now = get_utc_time()
        return (
            db.query(UserSession)
            .filter(
                UserSession.telegram_id == telegram_id,
                UserSession.expires_at > now,
            )
            .order_by(UserSession.created_at.desc())
            .all()
        )

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def refresh_session_ttl(
    telegram_id: int,
    session_type: SessionType,
    *,
    hours: Optional[float] = None,
    session: Optional[OrmSession] = None,
) -> Optional[UserSession]:
    """Extend the expiration of the active session and refresh Redis TTL.

    Returns the updated session or None if not found.
    """

    def _op(db: OrmSession) -> Optional[UserSession]:
        sess = UserSession.get_active_session(db, telegram_id, session_type)
        if not sess:
            return None
        ttl_hours = float(hours or SESSION_TIMEOUT_HOURS or 1)
        sess.expires_at = get_utc_time() + timedelta(hours=ttl_hours)
        sess.updated_at = get_utc_time()
        db.add(sess)
        db.flush()

        # Mirror to Redis
        key = _redis_key(telegram_id, session_type)
        try:
            r = _get_redis()
            payload = {
                "telegram_id": telegram_id,
                "session_type": session_type.value,
                "target_user_id": sess.target_user_id,
                "current_step": sess.current_step,
                "session_data": sess.session_data or {},
                "expires_at": sess.expires_at.isoformat(),
            }
            r.setex(key, int(ttl_hours * 3600), json.dumps(payload))
        except Exception as re:
            logger.warning(f"[SessionService] Redis TTL refresh failed: {re}")
        return sess

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def get_session_data(
    telegram_id: int,
    session_type: SessionType,
    *,
    session: Optional[OrmSession] = None,
) -> Optional[Dict[str, Any]]:
    """Convenience helper to fetch the session_data JSON payload."""

    def _op(db: OrmSession) -> Optional[Dict[str, Any]]:
        sess = UserSession.get_active_session(db, telegram_id, session_type)
        return (sess.session_data or {}) if sess else None

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def set_session_data(
    telegram_id: int,
    session_type: SessionType,
    data: Dict[str, Any],
    *,
    session: Optional[OrmSession] = None,
) -> UserSession:
    """Alias to update session JSON payload, ensuring TTL refresh."""
    updated = update_session_data(telegram_id, session_type, data, session=session)
    # Also refresh TTL to keep session alive when data changes
    try:
        refresh_session_ttl(telegram_id, session_type, session=session)
    except Exception:
        pass
    return updated


def clear_all_sessions(
    telegram_id: int,
    *,
    session: Optional[OrmSession] = None,
) -> None:
    """Clear all active sessions of any type for a user, including Redis keys."""

    def _op(db: OrmSession) -> None:
        sessions = get_active_sessions(telegram_id, session=db)
        for s in sessions:
            try:
                db.delete(s)
            except Exception:
                pass
        db.flush()
        # Delete Redis keys for known session types
        try:
            r = _get_redis()
            for st in SessionType:
                r.delete(_redis_key(telegram_id, st))
        except Exception as re:
            logger.warning(f"[SessionService] Redis bulk delete failed: {re}")

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)