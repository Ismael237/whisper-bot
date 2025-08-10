from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from database.models import SessionType
from services.session_service import get_active_session
from utils.logger import logger
from bot import keyboards
from services.link_service import generate_or_get_link
from services.user_service import get_user_by_telegram_id

# Import step constants and handlers to delegate
from bot.handlers.message_handler import (
    SEND_STEP_AWAITING_MESSAGE,
    handle_incoming_message,
)
from bot.handlers.delete_handler import (
    DELETE_STEP_AWAITING_CONFIRMATION,
    handle_delete_text,
)
from bot.handlers.play_handler import (
    PLAY_STEP_AWAITING_USERNAME,
    handle_username_input,
)
from bot.handlers import play_handler, inbox_handler, stats_handler, delete_handler


async def route_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Single entry point for free text messages.

    Decides where to route based on the user's active session and current step.
    Priority order:
      1) Sending an anonymous message (SENDING_MESSAGE/awaiting_message)
      2) Delete confirmation (SETUP/awaiting_delete_confirmation)
      3) Play setup username (SETUP/awaiting_username)
    If none match, it silently returns (no-op) to preserve previous behavior.
    """
    try:
        if not update.message or not update.message.text:
            return

        tg_user = update.effective_user
        if not tg_user:
            return

        # 0) High-priority: reply keyboard buttons (exact text match)
        text = update.message.text.strip()
        if text == keyboards.BTN_PLAY:
            await play_handler.handle_play(update, context)
            return
        if text == keyboards.BTN_MY_INBOX:
            await inbox_handler.handle_inbox_command(update, context)
            return
        if hasattr(keyboards, "BTN_STATS") and text == keyboards.BTN_STATS:
            await stats_handler.handle_stats(update, context)
            return
        if text == keyboards.BTN_SETTINGS:
            await update.message.reply_text("Settings", reply_markup=keyboards.get_settings_menu())
            return
        if text == keyboards.BTN_HELP:
            await update.message.reply_text("Help", reply_markup=keyboards.get_help_menu())
            return
        if text == keyboards.BTN_BACK_TO_MENU:
            await update.message.reply_text("Main menu", reply_markup=keyboards.get_main_menu())
            return
        if text == getattr(keyboards, "BTN_CHANGE_NAME", "__NO__"):
            await play_handler.handle_play(update, context)
            return
        if text == getattr(keyboards, "BTN_DELETE_ACCOUNT", "__NO__"):
            await delete_handler.handle_delete_command(update, context)
            return
        if text == getattr(keyboards, "BTN_SHARE_MY_LINK", "__NO__"):
            # Build or fetch the user's share link and show an inline Share button
            try:
                current_user = get_user_by_telegram_id(tg_user.id)
                desired = (current_user.username or None) if current_user else None
                link_res = generate_or_get_link(telegram_id=tg_user.id, desired_username=desired or f"Player-{tg_user.id}")
                share_kb = keyboards.get_inline_share_button_for_code(context.bot.username or "WhisperBot", link_res.code)
                await update.message.reply_text(
                    "Share your link with friends:",
                    reply_markup=share_kb,
                    disable_web_page_preview=True,
                )
            except Exception:
                await update.message.reply_text("Failed to generate share link. Try again later.")
            return
        if text == getattr(keyboards, "BTN_HELP_HOW_IT_WORKS", "__NO__"):
            msg = (
                "• Create your unique link in Play.\n"
                "• Share it so people can send you anonymous messages.\n"
                "• Read them in My Inbox.\n"
                "• You can change name or delete account in Settings."
            )
            await update.message.reply_text(msg, reply_markup=keyboards.get_help_menu())
            return
        if text == getattr(keyboards, "BTN_CONTACT_SUPPORT", "__NO__"):
            await update.message.reply_text("Contact: support@example.com", reply_markup=keyboards.get_help_menu())
            return

        # 1) Sending anonymous message flow
        sending_sess = get_active_session(tg_user.id, SessionType.SENDING_MESSAGE)
        if sending_sess and (sending_sess.current_step or "") == SEND_STEP_AWAITING_MESSAGE:
            await handle_incoming_message(update, context)
            return

        # 2) Delete account confirmation flow
        setup_sess = get_active_session(tg_user.id, SessionType.SETUP)
        if setup_sess and (setup_sess.current_step or "") == DELETE_STEP_AWAITING_CONFIRMATION:
            await handle_delete_text(update, context)
            return

        # 3) Play setup username flow
        if setup_sess and (setup_sess.current_step or "") == PLAY_STEP_AWAITING_USERNAME:
            await handle_username_input(update, context)
            return

        # No matching flow -> ignore to keep old behavior (handlers themselves were silent otherwise)
        return

    except Exception as e:
        logger.error(f"[TextRouter] Error routing free text: {e}")
        # Do not send a message here to avoid conflicting with downstream handlers
