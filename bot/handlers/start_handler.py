from telegram import Update
from telegram.ext import ContextTypes
from bot import messages, keyboards
from utils.logger import logger
from services.user_service import ensure_user
from services.session_service import create_or_get_session, set_current_step
from database.models import SessionType, User
from services.link_service import validate_start_parameter
from database.database import get_db_session


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start: ensure user exists (passive), sync @username, and either show menu or process deep-link.

    Deep-link flow (Feature 3.1):
    - Detect /start <code>
    - Validate code shape
    - Resolve target user by unique_code
    - Block self-send
    - Create SENDING_MESSAGE session with target_user_id
    - Set step to 'awaiting_message' (standardized)
    - Show prompt to send anonymous message
    """
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

        # Parse /start parameter if any
        text = update.message.text if hasattr(update, "message") and update.message else ""
        parts = (text or "").split(maxsplit=1)
        start_param = parts[1] if len(parts) > 1 else None

        if start_param:
            # Validate shape
            code = validate_start_parameter(start_param)
            if not code:
                await update.message.reply_markdown_v2(
                    messages.get_error_message("invalid_link"),
                )
                # Fall back to welcome menu
                create_or_get_session(
                    telegram_id=tg_user.id,
                    session_type=SessionType.SETUP,
                    initial_data={"entered_via": "start", "chat_id": chat.id if chat else None},
                )
                welcome_message = messages.get_welcome_message(tg_user.first_name or tg_user.full_name)
                await update.message.reply_markdown_v2(welcome_message, reply_markup=keyboards.get_main_menu())
                return

            # Resolve target user by unique_code
            with get_db_session() as db:
                target = db.query(User).filter(User.unique_code == code).first()

            if not target:
                await update.message.reply_markdown_v2(
                    messages.get_error_message("invalid_link"),
                )
                # Fall back to welcome
                create_or_get_session(
                    telegram_id=tg_user.id,
                    session_type=SessionType.SETUP,
                    initial_data={"entered_via": "start", "chat_id": chat.id if chat else None},
                )
                welcome_message = messages.get_welcome_message(tg_user.first_name or tg_user.full_name)
                await update.message.reply_markdown_v2(welcome_message, reply_markup=keyboards.get_main_menu())
                return

            # Block self-send
            if target.telegram_id == tg_user.id:
                await update.message.reply_markdown_v2(
                    messages.get_error_message("self_send_not_allowed"),
                )
                # Show main menu
                create_or_get_session(
                    telegram_id=tg_user.id,
                    session_type=SessionType.SETUP,
                    initial_data={"entered_via": "start", "chat_id": chat.id if chat else None},
                )
                await update.message.reply_markdown_v2(
                    messages.get_welcome_message(tg_user.first_name or tg_user.full_name),
                    reply_markup=keyboards.get_main_menu(),
                )
                return

            # Create SENDING_MESSAGE session targeting the recipient and set awaiting_message
            create_or_get_session(
                telegram_id=tg_user.id,
                session_type=SessionType.SENDING_MESSAGE,
                target_user_id=target.id,
                initial_data={
                    "entered_via": "deep_link",
                    "chat_id": chat.id if chat else None,
                    "target_code": code,
                },
            )
            set_current_step(tg_user.id, SessionType.SENDING_MESSAGE, "awaiting_message")

            # Display send prompt (do not capture/store text in 3.1)
            recipient_label = f"@{(target.telegram_username or '').lstrip('@')}" if target.telegram_username else target.username
            await update.message.reply_markdown_v2(
                messages.get_send_prompt(recipient_label),
                reply_markup=keyboards.get_main_menu(),
            )
            return

        # No start param: default welcome + SETUP session
        create_or_get_session(
            telegram_id=tg_user.id,
            session_type=SessionType.SETUP,
            initial_data={"entered_via": "start", "chat_id": chat.id if chat else None},
        )

        # Reply with welcome and main menu
        welcome_message = messages.get_welcome_message(tg_user.first_name or tg_user.full_name)
        await update.message.reply_markdown_v2(
            welcome_message,
            reply_markup=keyboards.get_main_menu(),
        )

    except Exception as e:
        logger.error(f"[StartHandler] Error in /start: {e}")
        message = messages.get_error_message("generic_error")
        await update.message.reply_markdown_v2(
            message,
            reply_markup=keyboards.get_main_menu(),
        )
