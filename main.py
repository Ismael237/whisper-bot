from telegram.ext import Application, CommandHandler
from bot.handlers import start_handler
from utils.logger import logger
from config import TELEGRAM_BOT_TOKEN


def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_handler.handle_start))
    
    # Log all errors
    application.add_error_handler(error_handler)

    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling()

async def error_handler(update: object, context) -> None:
    """Log the error and send a message to the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Send a message to the user
    if update and hasattr(update, 'message') and update.message:
        await update.message.reply_text(
            "An error occurred while processing your request. Please try again later."
        )

if __name__ == "__main__":
    logger.info("[Main] Runn de l'application principale.")
    main()
