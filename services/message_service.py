from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session as OrmSession
from sqlalchemy import desc, func

from database.database import get_db_session
from database.models import AnonymousMessage, User, ActivityLog, ActionType, SessionType 
from utils.validators import validate_message_length
from utils.time_utils import get_utc_time
from utils.logger import logger
from services.session_service import create_or_get_session, set_session_data, get_session_data
from config import RATE_LIMIT_MESSAGES_PER_HOUR, ENABLE_FLOOD_PROTECTION


def create_anonymous_message(
    *,
    recipient_user_id: int,
    sender_telegram_id: int,
    content: str,
    session: Optional[OrmSession] = None,
) -> AnonymousMessage:
    """Persist an anonymous message from sender to recipient with validation.

    - Validates message length/content
    - Ensures recipient exists
    - Increments counters for recipient (received) and sender (sent) if registered
    - Logs action to ActivityLog
    """

    ok, normalized_or_err = validate_message_length(content)
    if not ok:
        raise ValueError(normalized_or_err)
    text = normalized_or_err

    def _op(db: OrmSession) -> AnonymousMessage:
        # Lightweight anti-spam: rate limit per hour per sender
        try:
            if ENABLE_FLOOD_PROTECTION:
                try:
                    limit_per_hour = int(RATE_LIMIT_MESSAGES_PER_HOUR)
                except Exception:
                    limit_per_hour = 10
                if limit_per_hour > 0:
                    one_hour_ago = get_utc_time().replace(microsecond=0)
                    from datetime import timedelta
                    one_hour_ago = one_hour_ago - timedelta(hours=1)
                    sent_count = (
                        db.query(func.count(AnonymousMessage.id))
                        .filter(
                            AnonymousMessage.sender_telegram_id == sender_telegram_id,
                            AnonymousMessage.created_at >= one_hour_ago,
                        )
                        .scalar()
                        or 0
                    )
                    if sent_count >= limit_per_hour:
                        raise ValueError("⏳ Please wait before sending another message.")
        except ValueError:
            # Bubble up friendly validation errors
            raise
        except Exception as rl_ex:
            # Non-fatal: if rate-limit check fails, proceed without blocking
            logger.warning(f"[MessageService] Rate limit check failed: {rl_ex}")
        recipient = db.query(User).filter(User.id == recipient_user_id).first()
        if recipient is None:
            raise ValueError("Recipient not found")

        # Sender may or may not be a registered/active user; try fetch
        sender = db.query(User).filter(User.telegram_id == sender_telegram_id).first()

        message = AnonymousMessage(
            recipient_id=recipient.id,
            sender_telegram_id=sender_telegram_id,
            message_content=text,
            created_at=get_utc_time(),
        )
        db.add(message)

        # Update counters
        try:
            recipient.increment_messages_received(db)
        except Exception:
            pass
        if sender is not None:
            try:
                sender.increment_messages_sent(db)
            except Exception:
                pass

        # Log action (best effort)
        try:
            ActivityLog.log_activity(
                db,
                telegram_id=sender_telegram_id,
                action_type=ActionType.SEND_MESSAGE,
                details={"recipient_user_id": recipient_user_id},
            )
        except Exception as log_ex:
            logger.warning(f"[MessageService] Failed to write activity log: {log_ex}")

        db.flush()
        return message

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def mark_message_as_read(*, message_id: int, session: Optional[OrmSession] = None) -> None:
    """Mark a message as read by its internal id (idempotent)."""

    def _op(db: OrmSession) -> None:
        msg = db.query(AnonymousMessage).filter(AnonymousMessage.id == message_id).first()
        if not msg:
            return
        try:
            msg.mark_as_read(db)
        except Exception:
            # Fallback: direct field update
            if not msg.is_read:
                msg.is_read = True
                from utils.time_utils import get_utc_time as _now
                msg.read_at = msg.read_at or _now()
                db.add(msg)
        db.flush()

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def mark_message_as_read_by_public_id(*, public_id: str, session: Optional[OrmSession] = None) -> None:
    """Mark a message as read by its public id (idempotent)."""

    def _op(db: OrmSession) -> None:
        msg = db.query(AnonymousMessage).filter(AnonymousMessage.public_id == public_id).first()
        if not msg:
            return
        try:
            msg.mark_as_read(db)
        except Exception:
            if not msg.is_read:
                msg.is_read = True
                from utils.time_utils import get_utc_time as _now
                msg.read_at = msg.read_at or _now()
                db.add(msg)
        db.flush()

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


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
    pos = max(0, pos)
    try:
        logger.debug(f"[MessageService] get_current_position tg:{telegram_id} -> {pos}")
    except Exception:
        pass
    return pos


def set_position(telegram_id: int, position: int) -> int:
    position = max(0, int(position))
    try:
        logger.debug(f"[MessageService] set_position tg:{telegram_id} -> {position}")
    except Exception:
        pass
    try:
        logger.debug(f"[MessageService] set_position tg:{telegram_id} -> {position}")
    except Exception:
        pass
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
                try:
                    logger.debug(f"[MessageService] move_position tg:{telegram_id} current={current} delta={delta} -> {new_pos} (total={total})")
                except Exception:
                    pass
    return set_position(telegram_id, new_pos)


def move_and_get_page(
    telegram_id: int,
    delta: int,
    *,
    session: Optional[OrmSession] = None,
) -> tuple["InboxPage", bool, bool]:
    """Move position by delta with clamping and return (page, hit_lower_bound, hit_upper_bound).

    - hit_lower_bound: True if a negative move was requested but position couldn't decrease.
    - hit_upper_bound: True if a positive move was requested but position couldn't increase (at last item).
    """
    # Capture original position before move
    original_pos = get_current_position(telegram_id)
    # Use existing bounded move
    new_pos = move_position(telegram_id, delta, clamp_to_total=True)
    page = get_page_by_index(telegram_id, new_pos, session=session)

    hit_lower = delta < 0 and new_pos == original_pos
    hit_upper = delta > 0 and new_pos == original_pos
    return page, hit_lower, hit_upper


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
        if msg is not None:
            try:
                # Mark-as-read on display (idempotent)
                mark_message_as_read(message_id=msg.id, session=db)
            except Exception:
                pass
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