from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.handlers import start_handler
from bot.handlers import play_handler
from bot.handlers import inbox_handler
from bot.handlers import stats_handler
from bot.handlers import delete_handler
from bot.handlers import text_router
from utils.logger import logger, setup_logger
from config import LOG_LEVEL
from config import TELEGRAM_BOT_TOKEN
from database.database import init_db
from bot.middleware import session_middleware
import asyncio


def main() -> None:
    """Start the bot."""
    # Create the Application with a post_init hook so we can start schedulers
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    # Add handlers
    # Middleware-like pre-processor with high priority group
    application.add_handler(MessageHandler(filters.ALL, session_middleware), group=-100)
    application.add_handler(CommandHandler("start", start_handler.handle_start))
    application.add_handler(CommandHandler("play", play_handler.handle_play))
    application.add_handler(CommandHandler("inbox", inbox_handler.handle_inbox_command))
    application.add_handler(CommandHandler("stats", stats_handler.handle_stats))
    application.add_handler(CommandHandler("delete", delete_handler.handle_delete_command))
    
    # Capture all free text (including reply keyboard buttons) via a single router
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router.route_free_text))

    # Inline navigation for Inbox (1-based index: inbox_1, inbox_2, ...)
    application.add_handler(CallbackQueryHandler(inbox_handler.handle_inbox_navigation, pattern=r"^inbox_\d+$"))
    application.add_handler(CallbackQueryHandler(inbox_handler.handle_inbox_navigation, pattern=r"^share_msg:.*$"))
    application.add_handler(CallbackQueryHandler(delete_handler.handle_delete_callback, pattern=r"^delete_.*$"))
    
    # Log all errors
    application.add_error_handler(error_handler)

    # Configure logging level
    try:
        setup_logger(LOG_LEVEL)
    except Exception:
        pass

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

async def _post_init(app: Application) -> None:
    """Async post-init to start background schedulers after the event loop is running."""
    try:
        # Defer imports to avoid overhead if not needed and to keep main import fast
        from jobs.cleanup_job import setup_cleanup_scheduler
        from jobs.stats_job import setup_stats_scheduler

        # Use the currently running event loop
        loop = asyncio.get_running_loop()
        scheduler = AsyncIOScheduler(event_loop=loop)
        setup_cleanup_scheduler(scheduler)
        setup_stats_scheduler(scheduler)
        scheduler.start()
        # Optionally keep a reference on the app
        app.bot_data["scheduler"] = scheduler
        logger.info("Schedulers started")
    except Exception as sched_ex:
        logger.warning(f"[Main] Failed to start schedulers: {sched_ex}")

if __name__ == "__main__":
    logger.info("[Main] Running main application...")
    main()
