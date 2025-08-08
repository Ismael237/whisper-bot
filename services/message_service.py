from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session as OrmSession
from sqlalchemy import func

from database.database import get_db_session
from database.models import AnonymousMessage, User, ActivityLog, ActionType
from utils.validators import validate_message_length
from utils.helpers import get_utc_time
from utils.logger import logger
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


