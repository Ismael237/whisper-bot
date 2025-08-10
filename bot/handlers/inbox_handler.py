from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from bot import messages, keyboards
from services.image_service import create_share_card
from config import BOT_USERNAME
import os
import re
from services.sharing_service import get_message_share_url, increment_share_count
from services.message_service import (
    ensure_inbox_session,
    get_current_page,
    set_position,
    get_page_by_index,
    get_message_by_id,
)
from utils.logger import logger


def _build_inbox_view_text(page) -> str:
    """Build MarkdownV2 text for the inbox view (escaping handled by messages module)."""
    content = page.message.message_content if page.message else ""
    return messages.format_inbox_message(page.current_index, page.total_count, content)


def _build_inbox_keyboard(page):
    """Build navigation keyboard with share action, hiding prev/next at bounds."""
    share_cb = f"share_inbox_msg_{page.message.id}" if page.message else "share_inbox_msg_"
    return keyboards.get_inbox_keyboard_with_share(
        current_index=page.current_index,
        total=page.total_count,
        share_callback_data=share_cb,
    )


async def handle_share_inbox_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle share action for inbox given a message public_id."""
    logger.debug(f"[InboxHandler] share requested from tg:{update.effective_user.id}")
    try:
        if not update.callback_query:
            return
        query = update.callback_query
        data = query.data or ""
    except Exception:
        pass

    # Fetch message by its internal id from callback data
    m_share = re.match(r"^share_inbox_msg_(\d+)$", data)
    if not m_share:
        return
    message_id = int(m_share.group(1))
    msg = get_message_by_id(message_id)
    if not msg:
        try:
            await query.answer("Message introuvable.", show_alert=True)
        except Exception:
            pass
        return

    # Build share URL
    public_id = getattr(msg, "public_id", None) or ""
    url = get_message_share_url(public_id) if public_id else ""
    try:
        logger.debug(f"[InboxHandler] share requested public_id='{public_id}', url='{url}'")
    except Exception:
        pass

    # Use fetched message content
    msg_text = msg.message_content or ""

    # Resolve asset paths (fonts only)
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        title_font_path = os.path.join(project_root, "assets", "fonts", "Poppins-Bold.ttf")
        body_font_path = os.path.join(project_root, "assets", "fonts", "Poppins-SemiBold.ttf")
    except Exception:
        title_font_path = "assets/fonts/Poppins-Bold.ttf"
        body_font_path = "assets/fonts/Poppins-SemiBold.ttf"

    # Create and send image card with share URL button
    try:
        img_io = create_share_card(
            message_text=msg_text,
            bot_username=BOT_USERNAME,
            title_font_path=title_font_path,
            body_font_path=body_font_path,
        )
        caption = "📢 Share this in your story to reply"
        await query.message.reply_photo(photo=img_io, caption=caption)
    except Exception as ex:
        logger.warning(f"[InboxHandler] Failed to generate/share image: {ex}")
        # fallback: show URL share button
        await query.edit_message_reply_markup(reply_markup=keyboards.get_share_url_keyboard(url))
    # Increment share count (best-effort)
    try:
        if public_id:
            increment_share_count(public_id)
    except Exception as ex:
        logger.warning(f"[InboxHandler] Failed to increment share count: {ex}")
    try:
        await query.answer()
    except Exception:
        pass


async def handle_inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point for /inbox command or Inbox button.

    - Ensure inbox session and default position
    - Render current page or empty state
    """
    try:
        tg_user = update.effective_user
        # Ensure an inbox session exists; navigation relies on session data storage
        try:
            ensure_inbox_session(tg_user.id)
        except Exception as sess_ex:
            logger.warning(f"[InboxHandler] ensure_inbox_session failed: {sess_ex}")
        page = get_current_page(tg_user.id)

        if page.total_count == 0 or page.message is None:
            await update.message.reply_markdown_v2(messages.get_no_messages_message())
            return

        text = _build_inbox_view_text(page)
        nav = _build_inbox_keyboard(page)
        await update.message.reply_text(text, reply_markup=nav, parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"[InboxHandler] Error in handle_inbox_command: {e}")
        await update.message.reply_markdown_v2(messages.get_error_message("generic_error"))


async def handle_inbox_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button presses for inbox navigation."""
    try:
        if not update.callback_query:
            return
        query = update.callback_query
        data = query.data or ""

        tg_user = update.effective_user
        # Ensure inbox session exists for navigation (session data stores position)
        try:
            ensure_inbox_session(tg_user.id)
        except Exception as sess_ex:
            logger.warning(f"[InboxHandler] ensure_inbox_session (nav) failed: {sess_ex}")
        try:
            logger.debug(f"[InboxHandler] callback received from tg:{tg_user.id} data='{data}'")
        except Exception:
            pass

        # Direct index navigation: inbox_{n} where n is 1-based
        m = re.match(r"^inbox_(\d+)$", data)
        if not m:
            await query.answer()
            try:
                logger.debug(f"[InboxHandler] ignored callback data='{data}'")
            except Exception:
                pass
            return
        idx_1based = int(m.group(1))
        idx_0based = max(0, idx_1based - 1)
        try:
            logger.debug(f"[InboxHandler] navigating to index (1-based)={idx_1based} -> (0-based)={idx_0based}")
        except Exception:
            pass
        set_position(tg_user.id, idx_0based)
        page = get_page_by_index(tg_user.id, idx_0based)

        if page.total_count == 0 or page.message is None:
            await query.answer()
            await query.edit_message_text(messages.get_no_messages_message(), parse_mode=ParseMode.MARKDOWN_V2)
            try:
                logger.debug(f"[InboxHandler] empty inbox after move: total={page.total_count}")
            except Exception:
                pass
            return

        text = _build_inbox_view_text(page)
        nav = _build_inbox_keyboard(page)
        # Acknowledge the tap
        try:
            await query.answer()
        except Exception:
            pass
        try:
            # Telegram raises BadRequest("Message is not modified") when text and markup are identical.
            try:
                logger.debug(
                    f"[InboxHandler] editing message: idx={page.current_index} total={page.total_count} "
                    f"has_prev={page.has_previous} has_next={page.has_next}"
                )
            except Exception:
                pass
            await query.edit_message_text(text, reply_markup=nav, parse_mode=ParseMode.MARKDOWN_V2)
        except BadRequest as br:
            if "message is not modified" in str(br).lower():
                # Silently ignore: nothing changed (e.g., at bounds or duplicate click)
                try:
                    logger.debug("[InboxHandler] message not modified; ignoring")
                except Exception:
                    pass
                return
            raise
    except Exception as e:
        logger.error(f"[InboxHandler] Error in handle_inbox_navigation: {e}")
        try:
            if update.callback_query:
                await update.callback_query.answer()
        except Exception:
            pass

