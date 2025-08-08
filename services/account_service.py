from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session as OrmSession

from database.database import get_db_session
from database.models import User, AnonymousMessage
from utils.logger import logger
from utils.helpers import get_utc_time
from services.session_service import clear_all_sessions


def delete_account(telegram_id: int, *, session: Optional[OrmSession] = None) -> None:
    """Deactivate user account and anonymize their messages."""

    def _op(db: OrmSession) -> None:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user is None:
            return

        # Deactivate user
        user.is_active = False
        user.updated_at = get_utc_time()
        db.add(user)

        # Anonymize sent messages (sender_telegram_id already stores sender id; for extra privacy we could set to 0)
        try:
            db.query(AnonymousMessage).filter(AnonymousMessage.sender_telegram_id == telegram_id).update(
                {AnonymousMessage.sender_telegram_id: 0}, synchronize_session=False
            )
        except Exception as ex:
            logger.warning(f"[AccountService] Failed to anonymize sent messages: {ex}")

        # Optionally anonymize received (we keep them, but they remain accessible in recipient inbox)

        # Clear all sessions
        try:
            clear_all_sessions(telegram_id, session=db)
        except Exception as sess_ex:
            logger.warning(f"[AccountService] Failed to clear sessions: {sess_ex}")

        db.flush()

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


