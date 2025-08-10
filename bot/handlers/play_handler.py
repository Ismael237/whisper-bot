from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from bot import messages, keyboards
from services.link_service import generate_or_get_link
from services.session_service import (
    create_or_get_session,
    set_current_step,
    get_active_session,
    clear_session,
)
from services.user_service import ensure_user, set_active_status, get_user_by_telegram_id
from database.models import SessionType
from utils.logger import logger
from utils.helpers import escape_markdown_v2


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

        # If user already has a display name, skip prompt and show ready/share directly
        current_user = get_user_by_telegram_id(tg_user.id)
        current_name = (current_user.username or "").strip() if current_user else ""
        if current_name:
            try:
                link_res = generate_or_get_link(telegram_id=tg_user.id, desired_username=current_name)
            except Exception as e:
                logger.error(f"[PlayHandler] generate_or_get_link in /play failed for existing name: {e}")
                await update.message.reply_text(
                    messages.get_error_message("generic_error"),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                return

            # Activate and clear any setup session
            set_active_status(tg_user.id, True)
            try:
                clear_session(tg_user.id, SessionType.SETUP)
            except Exception:
                pass

            ready_msg = messages.get_play_ready_message(link_res.user.username, link_res.link)
            await update.message.reply_text(
                ready_msg,
                reply_markup=keyboards.get_main_menu(),
                disable_web_page_preview=True,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
            return

        # Create or get SETUP session and set step
        create_or_get_session(
            telegram_id=tg_user.id,
            session_type=SessionType.SETUP,
            initial_data={"entered_via": "play", "chat_id": chat.id if chat else None},
        )
        set_current_step(tg_user.id, SessionType.SETUP, PLAY_STEP_AWAITING_USERNAME)

        # Prompt for username, suggest Telegram @username when available
        prompt = messages.get_play_prompt(
            tg_username=(f"@{tg_user.username}" if tg_user.username else None),
            current_display_name=(current_user.username if current_user else None),
        )
        await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboards.get_main_menu())

    except Exception as e:
        logger.error(f"[PlayHandler] Error in handle_play: {e}")
        await update.message.reply_text(
            messages.get_error_message("generic_error"),
            parse_mode=ParseMode.MARKDOWN_V2,
        )


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

        # Fetch current stored display name for comparison
        current_user = get_user_by_telegram_id(tg_user.id)
        current_name = (current_user.username or "").strip() if current_user else ""

        # If user didn't change their name
        # - If no current name: re-prompt to choose a name
        # - Else: skip renaming and show ready/share directly
        if (not text) or (current_name and text == current_name):
            if not current_name:
                prompt = messages.get_play_prompt(
                    tg_username=(f"@{tg_user.username}" if tg_user.username else None),
                    current_display_name=None,
                )
                await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboards.get_main_menu())
                return

            # Ensure link exists for current name
            try:
                link_res = generate_or_get_link(telegram_id=tg_user.id, desired_username=current_name)
            except Exception as e:
                # Fall back to generic error
                logger.error(f"[PlayHandler] generate_or_get_link failed for existing name: {e}")
                await update.message.reply_text(messages.get_error_message("generic_error"), parse_mode=ParseMode.MARKDOWN_V2)
                return

            # Activate and finish
            set_active_status(tg_user.id, True)
            try:
                clear_session(tg_user.id, SessionType.SETUP)
            except Exception:
                pass
            ready_msg = messages.get_play_ready_message(link_res.user.username, link_res.link)
            await update.message.reply_text(ready_msg, reply_markup=keyboards.get_main_menu(), disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN_V2)
            return

        # Try generate (or retrieve) link with multi-step username resolution
        # Priority: user input -> @tg_username -> tg_username -> full_name -> first_name -> fallback
        candidates: list[str] = []
        if text:
            candidates.append(text)
        if tg_user.username:
            candidates.append(f"@{tg_user.username}")
            candidates.append(tg_user.username)
        # Build name variants from Telegram profile
        full_name = " ".join([p for p in [tg_user.first_name, tg_user.last_name] if p]) if tg_user else None
        if full_name:
            candidates.append(full_name)
        if tg_user.first_name:
            candidates.append(tg_user.first_name)
        # Final fallback
        candidates.append(f"Player-{tg_user.id}")

        last_error: Exception | None = None
        link_res = None
        for cand in candidates:
            try:
                link_res = generate_or_get_link(telegram_id=tg_user.id, desired_username=cand)
                break
            except ValueError as ve:
                last_error = ve
                continue
            except Exception as ex:
                last_error = ex
                continue
        if link_res is None:
            # Could not resolve a valid name; report escaped error
            err_text = escape_markdown_v2(str(last_error) if last_error else "Unknown error")
            await update.message.reply_text(err_text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboards.get_main_menu())
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
        await update.message.reply_text(ready_msg, reply_markup=keyboards.get_main_menu(), disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN_V2)

    except Exception as e:
        logger.error(f"[PlayHandler] Error in handle_username_input: {e}")
        await update.message.reply_text(messages.get_error_message("generic_error"), parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboards.get_main_menu())


