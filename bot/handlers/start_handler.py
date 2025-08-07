import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot import messages, keyboards
from utils.helpers import get_utc_time

logger = logging.getLogger(__name__)

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    try:
        user = update.effective_user
        logger.info(f"New user started the bot: {user.id} - {user.username}")
        
        welcome_message = messages.get_welcome_message(user.first_name)
        reply_markup = keyboards.get_main_menu()
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}", exc_info=True)
        await update.message.reply_text(
            "An error occurred while processing your request. Please try again."
        )
