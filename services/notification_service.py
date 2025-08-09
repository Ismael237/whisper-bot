from __future__ import annotations

from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN
from database.database import get_db_session
from database.models import User
from utils.logger import logger
from bot import messages
from bot import keyboards

async def notify_new_message(bot: Optional[Bot], *, recipient_user_id: int) -> None:
    """Send a simple Telegram notification to the recipient's chat.

    This uses the recipient's Telegram ID as chat id. If no bot instance is
    provided, one is created ad-hoc using TELEGRAM_BOT_TOKEN.
    """
    try:
        if bot is None:
            from telegram.ext import Application
            app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            bot = app.bot

        with get_db_session() as db:
            user = db.query(User).filter(User.id == recipient_user_id).first()
            if not user:
                return
            chat_id = user.telegram_id
        text = messages.get_new_message_notification()
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboards.get_main_menu())
    except Exception as e:
        logger.warning(f"[NotificationService] Failed to send notification: {e}")


