from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from bot import messages, keyboards
from services.inbox_service import (
    ensure_inbox_session,
    get_current_page,
    move_position,
)
from services.session_service import create_or_get_session
from database.models import SessionType
from utils.logger import logger


async def handle_inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for /inbox command or Inbox button.

    - Ensure inbox session and default position
    - Render current page or empty state
    """
    try:
        tg_user = update.effective_user
        ensure_inbox_session(tg_user.id)
        page = get_current_page(tg_user.id)

        if page.total_count == 0 or page.message is None:
            await update.message.reply_text(messages.get_no_messages_message())
            return

        text = messages.format_inbox_message(page.current_index, page.total_count, page.message.message_content)
        nav = keyboards.get_inbox_navigation_keyboard(page.has_previous, page.has_next)
        await update.message.reply_text(text, reply_markup=nav)
    except Exception as e:
        logger.error(f"[InboxHandler] Error in handle_inbox_command: {e}")
        await update.message.reply_text(messages.get_error_message("generic_error"))


async def handle_inbox_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button presses for inbox navigation."""
    try:
        if not update.callback_query:
            return
        query = update.callback_query
        data = query.data or ""

        tg_user = update.effective_user
        delta = 0
        if data == "inbox_prev":
            delta = -1
        elif data == "inbox_next":
            delta = +1
        elif data == "inbox_home":
            # Ensure SETUP session and show a simple home note (could be replaced by full menu)
            create_or_get_session(
                telegram_id=tg_user.id,
                session_type=SessionType.SETUP,
                initial_data={"entered_via": "inbox_home"},
            )
            await query.answer()
            await query.edit_message_text("🏠 Back to home. Use the main menu.")
            return
        else:
            await query.answer()
            return

        # Move position and render
        move_position(tg_user.id, delta)
        page = get_current_page(tg_user.id)

        if page.total_count == 0 or page.message is None:
            await query.answer()
            await query.edit_message_text(messages.get_no_messages_message())
            return

        text = messages.format_inbox_message(page.current_index, page.total_count, page.message.message_content)
        nav = keyboards.get_inbox_navigation_keyboard(page.has_previous, page.has_next)
        await query.answer()
        await query.edit_message_text(text, reply_markup=nav)
    except Exception as e:
        logger.error(f"[InboxHandler] Error in handle_inbox_navigation: {e}")
        try:
            if update.callback_query:
                await update.callback_query.answer()
        except Exception:
            pass

