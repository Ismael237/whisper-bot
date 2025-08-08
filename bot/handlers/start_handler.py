from telegram import Update
from telegram.ext import ContextTypes
from bot import messages, keyboards
from utils.logger import logger
from services.user_service import ensure_user
from services.session_service import create_or_get_session
from database.models import SessionType


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start: ensure user exists (passive), sync @username, create setup session, and show menu."""
    try:
        tg_user = update.effective_user
        chat = update.effective_chat
        logger.info(f"[StartHandler] /start from telegram_id={tg_user.id} username={tg_user.username}")

        # Ensure user exists (passive) and sync telegram_username
        sync_result = ensure_user(
            telegram_id=tg_user.id,
            telegram_username=tg_user.username,
            default_display_name=tg_user.first_name or tg_user.username or "Player",
            is_active=False,
            extra_details={"command": "/start"},
        )

        # Create or refresh a setup session in DB + Redis
        create_or_get_session(
            telegram_id=tg_user.id,
            session_type=SessionType.SETUP,
            initial_data={"entered_via": "start", "chat_id": chat.id if chat else None},
        )

        # Reply with welcome and main menu
        welcome_message = messages.get_welcome_message(tg_user.first_name or tg_user.full_name)
        reply_markup = keyboards.get_main_menu()
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"[StartHandler] Error in /start: {e}")
        message = messages.get_error_message("generic_error")
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
