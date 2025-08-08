from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot import messages
from services.session_service import get_active_session, clear_session
from services.message_service import create_anonymous_message
from database.models import SessionType
from utils.logger import logger


SEND_STEP_AWAITING_MESSAGE = "awaiting_message"


async def handle_incoming_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture free-text when user is in SENDING_MESSAGE/awaiting_message.

    - Validate and persist the anonymous message
    - Clear SENDING_MESSAGE session
    - Confirm to the sender and show a minimal follow-up
    """
    try:
        if not update.message or not update.message.text:
            return

        tg_user = update.effective_user
        text = update.message.text.strip()

        sess = get_active_session(tg_user.id, SessionType.SENDING_MESSAGE)
        if not sess or (sess.current_step or "") != SEND_STEP_AWAITING_MESSAGE:
            return

        if not sess.target_user_id:
            await update.message.reply_text(messages.get_error_message("generic_error"))
            try:
                clear_session(tg_user.id, SessionType.SENDING_MESSAGE)
            except Exception:
                pass
            return

        # Persist message
        try:
            create_anonymous_message(
                recipient_user_id=sess.target_user_id,
                sender_telegram_id=tg_user.id,
                content=text,
            )
        except ValueError as ve:
            await update.message.reply_text(str(ve))
            return

        # Clear session after successful send
        try:
            clear_session(tg_user.id, SessionType.SENDING_MESSAGE)
        except Exception:
            pass

        # Confirm to the sender
        await update.message.reply_text(messages.get_success_message("message_sent"))

    except Exception as e:
        logger.error(f"[MessageHandler] Error in handle_incoming_message: {e}")
        await update.message.reply_text(messages.get_error_message("generic_error"))


