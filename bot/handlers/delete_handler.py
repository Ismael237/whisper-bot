from __future__ import annotations

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from services.user_service import delete_account
from services.session_service import clear_all_sessions
from utils.logger import logger
from utils.helpers import escape_markdown_v2 as _esc, get_separator as _sep


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Yes, delete my account", callback_data="delete_confirm")],
            [InlineKeyboardButton("Cancel", callback_data="delete_cancel")]
        ]
    )


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Cancel", callback_data="delete_cancel")]
        ]
    )


DELETE_STEP_AWAITING_CONFIRMATION = "awaiting_delete_confirmation"


async def handle_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = (
            "*⚠️ Confirm deletion*\n"
            f"{_sep()}\n"
            "This will deactivate your account and anonymize your sent messages\\.\n"
            "This action cannot be undone\\.\n\n"
            "If you agree, tap *Yes, delete my account*\\."
        )
        await update.message.reply_markdown_v2(text, reply_markup=_confirm_keyboard())
    except Exception as e:
        logger.error(f"[DeleteHandler] Error in /delete: {e}")
        await update.message.reply_markdown_v2("❌ Failed to start deletion flow\\.")


async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not update.callback_query:
            return
        query = update.callback_query
        data = query.data or ""
        tg_user = update.effective_user

        if data == "delete_confirm":
            # Double confirmation: require typing DELETE
            from services.session_service import create_or_get_session, set_current_step
            # Proper explicit import and usage of SessionType
            from database.models import SessionType as _SessionType
            create_or_get_session(
                telegram_id=tg_user.id,
                session_type=_SessionType.SETUP,
            )
            set_current_step(tg_user.id, _SessionType.SETUP, DELETE_STEP_AWAITING_CONFIRMATION)
            await query.answer()
            await query.edit_message_text(
                "*Final step*\\: Type *DELETE* to confirm account deletion\\.\n"
                f"{_sep()}\n"
                "This cannot be undone\\.",
                reply_markup=_cancel_keyboard(),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        elif data == "delete_cancel":
            await query.answer()
            await query.edit_message_text("❎ Deletion canceled\\.", parse_mode=ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"[DeleteHandler] Error in delete callback: {e}")
        try:
            if update.callback_query:
                await update.callback_query.answer()
        except Exception:
            pass


async def handle_delete_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture text input for strict delete confirmation.

    Only acts when SETUP session step is awaiting_delete_confirmation.
    """
    try:
        if not update.message or not update.message.text:
            return
        tg_user = update.effective_user
        from services.session_service import get_active_session
        from database.models import SessionType as _SessionType
        sess = get_active_session(tg_user.id, _SessionType.SETUP)
        if not sess or (sess.current_step or "") != DELETE_STEP_AWAITING_CONFIRMATION:
            return

        text = update.message.text.strip()
        if text == "DELETE":
            try:
                delete_account(tg_user.id)
                try:
                    clear_all_sessions(tg_user.id)
                except Exception:
                    pass
                await update.message.reply_markdown_v2(
                    "*🗑️ Account deleted*\n"
                    f"{_sep()}\n"
                    "Your account has been deactivated and your messages anonymized\\."
                )
            except Exception as ex:
                logger.error(f"[DeleteHandler] Delete failed: {ex}")
                await update.message.reply_markdown_v2("❌ Failed to delete account\\. Please try again later\\.")
            return

        await update.message.reply_markdown_v2(
            "Type *DELETE* to confirm or tap *Cancel*\\.", reply_markup=_cancel_keyboard()
        )
    except Exception as e:
        logger.error(f"[DeleteHandler] Error in handle_delete_text: {e}")


