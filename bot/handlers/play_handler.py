from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot import messages, keyboards
from services.link_service import generate_or_get_link
from services.session_service import (
    create_or_get_session,
    set_current_step,
    get_active_session,
    clear_session,
)
from services.user_service import ensure_user, set_active_status
from database.models import SessionType
from utils.logger import logger


PLAY_STEP_AWAITING_USERNAME = "awaiting_username"


async def handle_play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for /play command or Play button.

    - Ensures user exists
    - Starts/refreshes SETUP session and sets step to awaiting username
    - Prompts user for display name
    """
    try:
        tg_user = update.effective_user
        chat = update.effective_chat

        logger.info(f"[PlayHandler] /play from telegram_id={tg_user.id} username={tg_user.username}")

        # Ensure baseline user exists
        ensure_user(
            telegram_id=tg_user.id,
            telegram_username=tg_user.username,
            default_display_name=tg_user.first_name or tg_user.username or "Player",
            is_active=False,
            extra_details={"command": "/play"},
        )

        # Create or get SETUP session and set step
        create_or_get_session(
            telegram_id=tg_user.id,
            session_type=SessionType.SETUP,
            initial_data={"entered_via": "play", "chat_id": chat.id if chat else None},
        )
        set_current_step(tg_user.id, SessionType.SETUP, PLAY_STEP_AWAITING_USERNAME)

        # Prompt for username, suggest Telegram @username when available
        prompt = messages.get_play_prompt(
            tg_username=tg_user.username,
            current_display_name=None,
        )
        await update.message.reply_text(prompt)

    except Exception as e:
        logger.error(f"[PlayHandler] Error in handle_play: {e}")
        await update.message.reply_text(messages.get_error_message("generic_error"))


async def handle_username_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-text input when waiting for display name in Play flow.

    If session is not in awaiting_username step, this handler silently returns.
    """
    try:
        if not update.message or not update.message.text:
            return

        tg_user = update.effective_user
        text = update.message.text.strip()

        # Check active SETUP session and step
        sess = get_active_session(tg_user.id, SessionType.SETUP)
        if not sess or (sess.current_step or "") != PLAY_STEP_AWAITING_USERNAME:
            return

        # Try generate (or retrieve) link while applying desired username
        try:
            link_res = generate_or_get_link(telegram_id=tg_user.id, desired_username=text)
        except ValueError as ve:
            # Validation error from username rules
            await update.message.reply_text(str(ve))
            return

        # Activate account
        set_active_status(tg_user.id, True)

        # Clear step/session
        try:
            clear_session(tg_user.id, SessionType.SETUP)
        except Exception:
            # Non-fatal
            pass

        # Reply with ready message and share button
        ready_msg = messages.get_play_ready_message(link_res.user.username, link_res.link)
        share_kb = keyboards.get_inline_share_button_for_code(context.bot.username or "WhisperBot", link_res.code)
        await update.message.reply_text(ready_msg, reply_markup=share_kb, disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"[PlayHandler] Error in handle_username_input: {e}")
        await update.message.reply_text(messages.get_error_message("generic_error"))


