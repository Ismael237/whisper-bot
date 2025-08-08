from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from utils.helpers import generate_share_link

# Button texts
BTN_PLAY = "🎮 Play"
BTN_MY_INBOX = "📬 My Inbox"
BTN_SETTINGS = "⚙️ Settings"
BTN_HELP = "❓ Help"

def get_main_menu() -> ReplyKeyboardMarkup:
    """Create the main menu keyboard."""
    keyboard = [
        [KeyboardButton(BTN_PLAY), KeyboardButton(BTN_MY_INBOX)],
        [KeyboardButton(BTN_SETTINGS), KeyboardButton(BTN_HELP)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_inline_share_button(bot_username: str, user_id: int) -> InlineKeyboardMarkup:
    """Create an inline keyboard with a share button.
    
    Args:
        bot_username: The bot's username without @
        user_id: The user's Telegram ID
        
    Returns:
        InlineKeyboardMarkup: The share button keyboard
    """
    # In a real implementation, you might want to generate a unique code
    # for each user to handle the /start parameter
    share_url = generate_share_link(bot_username, user_id)
    keyboard = [
        [
            InlineKeyboardButton(
                "📤 Share your link",
                url=f"https://t.me/share/url?url={share_url}&text=Send%20me%20an%20anonymous%20message!"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_inline_share_button_for_code(bot_username: str, code: str) -> InlineKeyboardMarkup:
    """Create an inline keyboard with a share button for a specific start code.

    Args:
        bot_username: The bot's username without @
        code: The start parameter code (e.g., unique_code)

    Returns:
        InlineKeyboardMarkup: The share button keyboard
    """
    share_url = generate_share_link(bot_username, code)
    keyboard = [
        [
            InlineKeyboardButton(
                "📤 Share your link",
                url=f"https://t.me/share/url?url={share_url}&text=Send%20me%20an%20anonymous%20message!"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
