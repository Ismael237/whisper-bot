from bot.keyboards import BTN_PLAY
from utils.helpers import escape_markdown_v2 as _esc
from utils.helpers import get_separator as _sep

# Welcome message
def get_welcome_message(username: str) -> str:
    """Generate welcome message for new users (MarkdownV2)."""
    u = _esc(username)
    lines = [
        f"*👋 Welcome, {u}\\!*",
        _sep(),
        "🕵️ *Receive anonymous messages* — share your personal link and read replies privately\\.",
        "Here's how it works\\:",
        "1\\. Share your link with friends",
        "2\\. They send you anonymous messages",
        "3\\. Read them in your private inbox",
        _sep(),
        "🛡️ Your identity is never shown to senders\\.",
        f"▶️ Tap {BTN_PLAY} to set your display name and get your link\\!",
    ]
    return "\n".join(lines)

# Error messages (pre-escaped for MarkdownV2 where needed)
ERROR_MESSAGES = {
    'generic_error': "❌ An error occurred\\. Please try again\\.",
    'message_too_long': "❌ Message is too long\\. Maximum 1000 characters allowed\\.",
    'rate_limit': "⏳ Please wait before sending another message\\.",
    'username_validation': "❌ Invalid username\\. Please use a valid username\\.",
    'username_length': "❌ Invalid username\\. Please use a valid username\\.",
    'invalid_link': "❌ This link is invalid or expired\\.",
    'self_send_not_allowed': "❌ You cannot send an anonymous message to yourself\\.",
}

def get_error_message(error_key: str) -> str:
    """Get error message by key (MarkdownV2)."""
    return ERROR_MESSAGES.get(error_key, ERROR_MESSAGES['generic_error'])

# Success messages
SUCCESS_MESSAGES = {
    'message_sent': (
        "✅ Your anonymous message has been sent\\!\n"
        f"{_sep()}\n"
        f"If you want to receive anonymous messages yourself, tap the {BTN_PLAY} button\\!"
    ),
    'settings_updated': "⚙️ Settings updated successfully\\!"
}

def get_success_message(key: str) -> str:
    """Get success message by key (MarkdownV2)."""
    return SUCCESS_MESSAGES.get(key, "✅ Operation completed successfully\\!")

# Play messages
def get_play_prompt(tg_username: str | None, current_display_name: str | None) -> str:
    """Prompt asking the user to choose a display name (MarkdownV2).

    If a Telegram @username is available, we suggest it.
    """
    suggestion = f"💡 Suggested\: {_esc(tg_username)}" if tg_username else ""
    current = _esc(current_display_name) if current_display_name else "\\[Not set\\]"
    lines = [
        "*🎮 PLAY MODE*",
        _sep(),
        "Choose your display name\\:",
        "This name will be shown when people send you messages\\.",
        "\n",
        f"Current name\\: {current}",
    ]
    if suggestion:
        lines.append(suggestion)
    lines.append(_sep())
    lines.append("✍️ Enter your new display name below\\:")
    return "\n".join(lines)

def get_play_ready_message(username: str, link: str) -> str:
    """Message shown when the link is ready and the account is active (MarkdownV2)."""
    u = _esc(username)
    l = _esc(link)
    return (
        "*✅ Profile ready\\!*\n"
        f"{_sep()}\n"
        f"👤 *Name*\\: {u}\n\n"
        f"🔗 *Link\\(click to copy\\)*\\:\n"
        f"\n`{l}`\n\n"
        f"{_sep()}\n"
        "📤 Share it so friends can message you anonymously\\!"
    )

# Incoming link (send message) prompt
def get_send_prompt(recipient_label: str) -> str:
    """Prompt asking the user to type an anonymous message to the recipient (MarkdownV2).

    Args:
        recipient_label: Display label for the recipient (e.g., "@john" or "john")
    """
    rl = _esc(recipient_label)
    lines = [
        "*💬 Send an anonymous message*",
        _sep(),
        f"*Recipient*\\: {rl}",
        "💡 Be kind and specific for better replies\\.",
        "🛡️ 100% anonymous — your identity is never shared\\.",
        "✍️ Write your message below \\(max 100 characters\\)\\:",
    ]
    return "\n".join(lines)

# Notifications
def get_new_message_notification() -> str:
    """Notification text sent to recipient when a new message arrives (MarkdownV2)."""
    return (
        "*📬 New message received\\!*\n"
        "\n"
        "Open your Inbox to read it\\."
    )

# Inbox messages
def get_no_messages_message() -> str:
    """Shown when the inbox is empty (MarkdownV2)."""
    return (
        "*📭 No messages yet\\!*\n"
        f"{_sep()}\n"
        "Share your link to start receiving anonymous messages\\.\n"
        f"{_sep()}\n"
        "💡 Tip\\: Click on the link in your profile to copy and share your link with friends\\."
    )

def format_inbox_message(index: int, total: int, content: str) -> str:
    """Format the inbox view for a single message (MarkdownV2).

    Args:
        index: 0-based index in the list (newest first)
        total: total messages count
        content: message body
    """
    header = (
        f"*📬 INBOX* \\(Message {_esc(str(index + 1))} of {_esc(str(total))}\\)\n"
        f"{_sep()}\n\n"
    )
    title = ">> 🕵️ Anonymous message :"
    title += "\n>> "
    escaped = _esc(content or "")
    formatted = f"\n>> *{escaped}*"
    formatted += "\n>> "
    footer = f"\n{_sep()}"
    return header + title + formatted + footer