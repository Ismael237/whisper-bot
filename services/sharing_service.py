from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session as OrmSession

from database.database import get_db_session
from database.models import AnonymousMessage
from utils.logger import logger
from config import BOT_USERNAME
from utils.helpers import generate_share_link


def get_message_share_url(public_id: str) -> str:
    """Build a share URL for a specific message using its public id.

    For MVP, we use the same t.me link with the message public id as start parameter
    (could later point to a web view).
    """
    return generate_share_link(BOT_USERNAME, public_id)


def increment_share_count(public_id: str, *, session: Optional[OrmSession] = None) -> None:
    """Increment the share counter for a message by its public id."""

    def _op(db: OrmSession) -> None:
        msg = db.query(AnonymousMessage).filter(AnonymousMessage.public_id == public_id).first()
        if not msg:
            raise ValueError("Message not found")
        try:
            msg.increment_share_count(db)
        except Exception:
            # Fallback to manual increment if needed
            msg.shared_count = (msg.shared_count or 0) + 1
            db.add(msg)
        db.flush()

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


