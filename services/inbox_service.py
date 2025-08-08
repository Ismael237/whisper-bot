from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session as OrmSession
from sqlalchemy import desc, func

from database.database import get_db_session
from database.models import User, AnonymousMessage, SessionType
from services.session_service import create_or_get_session, set_session_data, get_session_data


INBOX_POSITION_KEY = "inbox_position"


@dataclass
class InboxPage:
    total_count: int
    current_index: int
    has_previous: bool
    has_next: bool
    message: Optional[AnonymousMessage]


def _get_user_by_telegram_id(db: OrmSession, telegram_id: int) -> Optional[User]:
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def _count_received(db: OrmSession, user_id: int) -> int:
    return db.query(func.count(AnonymousMessage.id)).filter(AnonymousMessage.recipient_id == user_id).scalar() or 0


def _fetch_message_at_index(db: OrmSession, user_id: int, index: int) -> Optional[AnonymousMessage]:
    if index < 0:
        return None
    return (
        db.query(AnonymousMessage)
        .filter(AnonymousMessage.recipient_id == user_id)
        .order_by(desc(AnonymousMessage.created_at))
        .offset(index)
        .limit(1)
        .first()
    )


def ensure_inbox_session(telegram_id: int) -> None:
    """Ensure an inbox browsing session exists with a default position of 0 if absent."""
    res = create_or_get_session(
        telegram_id=telegram_id,
        session_type=SessionType.BROWSING_INBOX,
        initial_data={INBOX_POSITION_KEY: 0},
    )
    # If session existed without the key, keep it idempotent by setting it
    data = get_session_data(telegram_id, SessionType.BROWSING_INBOX) or {}
    if INBOX_POSITION_KEY not in data:
        set_session_data(telegram_id, SessionType.BROWSING_INBOX, {INBOX_POSITION_KEY: 0})


def get_current_position(telegram_id: int) -> int:
    data = get_session_data(telegram_id, SessionType.BROWSING_INBOX) or {}
    pos = int(data.get(INBOX_POSITION_KEY, 0) or 0)
    return max(0, pos)


def set_position(telegram_id: int, position: int) -> int:
    position = max(0, int(position))
    set_session_data(telegram_id, SessionType.BROWSING_INBOX, {INBOX_POSITION_KEY: position})
    return position


def move_position(telegram_id: int, delta: int, *, clamp_to_total: bool = True) -> int:
    current = get_current_position(telegram_id)
    new_pos = current + int(delta)
    if new_pos < 0:
        new_pos = 0
    # Optionally clamp to total-1 if available
    if clamp_to_total:
        with get_db_session() as db:
            user = _get_user_by_telegram_id(db, telegram_id)
            if user:
                total = _count_received(db, user.id)
                if total > 0:
                    new_pos = min(new_pos, max(0, total - 1))
                else:
                    new_pos = 0
    return set_position(telegram_id, new_pos)


def get_page_by_index(telegram_id: int, index: int, *, session: Optional[OrmSession] = None) -> InboxPage:
    """Return a page model for the given index (0-based, newest first)."""

    def _op(db: OrmSession) -> InboxPage:
        user = _get_user_by_telegram_id(db, telegram_id)
        if user is None:
            return InboxPage(total_count=0, current_index=0, has_previous=False, has_next=False, message=None)

        total = _count_received(db, user.id)
        if total <= 0:
            return InboxPage(total_count=0, current_index=0, has_previous=False, has_next=False, message=None)

        idx = max(0, min(int(index), total - 1))
        msg = _fetch_message_at_index(db, user.id, idx)
        has_prev = idx > 0
        has_next = (idx + 1) < total
        return InboxPage(total_count=total, current_index=idx, has_previous=has_prev, has_next=has_next, message=msg)

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def get_current_page(telegram_id: int, *, session: Optional[OrmSession] = None) -> InboxPage:
    pos = get_current_position(telegram_id)
    page = get_page_by_index(telegram_id, pos, session=session)
    # Ensure stored position matches clamped index
    set_position(telegram_id, page.current_index)
    return page


