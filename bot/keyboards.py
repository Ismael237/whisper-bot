from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from utils.helpers import generate_share_link

# Button texts (main menu)
BTN_PLAY = "🎮 Play"
BTN_MY_INBOX = "📬 My Inbox"
BTN_STATS = "📈 Stats"
BTN_SETTINGS = "⚙️ Settings"
BTN_HELP = "❓ Help"

# Button texts (submenus)
BTN_BACK_TO_MENU = "⬅️ Back to Menu"

# Settings submenu buttons
BTN_CHANGE_NAME = "✏️ Change name"
BTN_DELETE_ACCOUNT = "🗑️ Delete account"
BTN_SHARE_MY_LINK = "📤 Share my link"

# Help submenu buttons
BTN_HELP_HOW_IT_WORKS = "📚 How it works"
BTN_CONTACT_SUPPORT = "🆘 Contact support"


def get_main_menu() -> ReplyKeyboardMarkup:
    """Create the main menu keyboard."""
    keyboard = [
        [KeyboardButton(BTN_PLAY)],
        [KeyboardButton(BTN_STATS), KeyboardButton(BTN_MY_INBOX)],
        [KeyboardButton(BTN_HELP), KeyboardButton(BTN_SETTINGS)],
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


def get_inbox_keyboard_with_share(
    *,
    current_index: int,
    total: int,
    share_callback_data: str,
) -> InlineKeyboardMarkup:
    """Inline keyboard including navigation and a Share button (callback).

    Uses 1-based indices in callback data: inbox_1, inbox_2, ...
    """
    rows = []
    nav_row = []

    # Previous button targets (current_index - 1) if available
    if current_index > 0 and total > 0:
        prev_target_1based = (current_index)  # (current_index-1) + 1
        nav_row.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"inbox_{prev_target_1based}"))

    # Next button targets (current_index + 1) if available
    if (current_index + 1) < total and total > 0:
        next_target_1based = (current_index + 2)  # (current_index+1) + 1
        nav_row.append(InlineKeyboardButton("➡️ Next", callback_data=f"inbox_{next_target_1based}"))

    if nav_row:
        rows.append(nav_row)

    share_row = [InlineKeyboardButton("📤 Share", callback_data=share_callback_data)]
    rows.append(share_row)

    return InlineKeyboardMarkup(rows)


def get_share_url_keyboard(share_url: str) -> InlineKeyboardMarkup:
    """Inline keyboard pointing to Telegram share interface for the given URL."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📤 Share", url=share_url)]]
    )


def get_settings_menu() -> ReplyKeyboardMarkup:
    """Reply keyboard for the Settings submenu."""
    keyboard = [
        [KeyboardButton(BTN_SHARE_MY_LINK)],
        [KeyboardButton(BTN_CHANGE_NAME), KeyboardButton(BTN_DELETE_ACCOUNT)],
        [KeyboardButton(BTN_BACK_TO_MENU)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_help_menu() -> ReplyKeyboardMarkup:
    """Reply keyboard for the Help submenu."""
    keyboard = [
        [KeyboardButton(BTN_HELP_HOW_IT_WORKS), KeyboardButton(BTN_CONTACT_SUPPORT)],
        [KeyboardButton(BTN_BACK_TO_MENU)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)