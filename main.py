from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.handlers import start_handler
from bot.handlers import play_handler
from bot.handlers import inbox_handler
from bot.handlers import stats_handler
from bot.handlers import delete_handler
from bot.handlers import message_handler
from utils.logger import logger
from config import TELEGRAM_BOT_TOKEN
from database.database import init_db
from bot import keyboards
import re
from bot.middleware import session_middleware


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    # Middleware-like pre-processor with high priority group
    application.add_handler(MessageHandler(filters.ALL, session_middleware), group=-100)
    application.add_handler(CommandHandler("start", start_handler.handle_start))
    application.add_handler(CommandHandler("play", play_handler.handle_play))
    application.add_handler(CommandHandler("inbox", inbox_handler.handle_inbox_command))
    application.add_handler(CommandHandler("stats", stats_handler.handle_stats))
    application.add_handler(CommandHandler("delete", delete_handler.handle_delete_command))
    
    # Map "🎮 Play" button press to the same handler
    play_btn = rf"^{re.escape(keyboards.BTN_PLAY)}$"
    application.add_handler(MessageHandler(filters.Regex(play_btn), play_handler.handle_play))
    # Map "📬 My Inbox" button press to inbox handler
    inbox_btn = rf"^{re.escape(keyboards.BTN_MY_INBOX)}$"
    application.add_handler(MessageHandler(filters.Regex(inbox_btn), inbox_handler.handle_inbox_command))
    # Capture free text: route to message handler first (when in SENDING_MESSAGE),
    # otherwise fall back to play username input and delete confirmation
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler.handle_incoming_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, delete_handler.handle_delete_text))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, play_handler.handle_username_input))

    # Inline navigation for Inbox
    application.add_handler(CallbackQueryHandler(inbox_handler.handle_inbox_navigation))
    application.add_handler(CallbackQueryHandler(delete_handler.handle_delete_callback))
    
    # Log all errors
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info("Starting bot...")
    # Ensure database tables are ready before processing updates
    try:
        init_db()
    except Exception as e:
        logger.error(f"[Main] Failed to initialize database: {e}")
    application.run_polling()

async def error_handler(update: object, context) -> None:
    """Log the error and send a message to the user."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Send a message to the user
    if update and hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            f"An error occurred while processing your request. Please try again later."
        )

if __name__ == "__main__":
    logger.info("[Main] Running main application...")
    main()
