
# Welcome message
def get_welcome_message(username: str) -> str:
    """Generate welcome message for new users."""
    msg = f"👋 *Welcome, {username} to Anonymous Message Bot!*\n\n"
    msg += "📨 *How it works:*\n"
    msg += "1. Share your personal link with friends\n"
    msg += "2. They can send you anonymous messages\n"
    msg += "3. Read messages in your private inbox\n\n"
    msg += "Use the buttons below to get started!"
    
    return msg

# Error messages
ERROR_MESSAGES = {
    'generic_error': "❌ An error occurred. Please try again.",
    'message_too_long': "❌ Message is too long. Maximum 1000 characters allowed.",
    'rate_limit': "⏳ Please wait before sending another message.",
    'username_validation': "❌ Invalid username. Please use a valid username.",
    'username_length': "❌ Invalid username. Please use a valid username.",
    'invalid_link': "❌ This link is invalid or expired.",
    'self_send_not_allowed': "❌ You cannot send an anonymous message to yourself.",
}

def get_error_message(error_key: str) -> str:
    """Get error message by key."""
    return ERROR_MESSAGES.get(error_key, ERROR_MESSAGES['generic_error'])

# Success messages
SUCCESS_MESSAGES = {
    'message_sent': "✅ Your anonymous message has been sent!",
    'settings_updated': "⚙️ Settings updated successfully!"
}

def get_success_message(key: str) -> str:
    """Get success message by key."""
    return SUCCESS_MESSAGES.get(key, "✅ Operation completed successfully!")


# Play messages
def get_play_prompt(tg_username: str | None, current_display_name: str | None) -> str:
    """Prompt asking the user to choose a display name.

    If a Telegram @username is available, we suggest it.
    """
    suggestion = f"Suggested: {tg_username}" if tg_username else ""
    current = current_display_name or "[Not set]"
    lines = [
        "🎮 PLAY MODE",
        "",
        "Choose your display name:",
        "This name will be shown when people send you messages.",
        "",
        f"Current name: {current}",
    ]
    if suggestion:
        lines.append(suggestion)
    lines.append("")
    lines.append("Enter your new display name:")
    return "\n".join(lines)


def get_play_ready_message(username: str, link: str) -> str:
    """Message shown when the link is ready and the account is active."""
    return (
        "✅ Your profile is ready!\n\n"
        f"Display name: {username}\n"
        f"Your link: {link}\n\n"
        "Share it so your friends can send you anonymous messages!"
    )


# Incoming link (send message) prompt
def get_send_prompt(recipient_label: str) -> str:
    """Prompt asking the user to type an anonymous message to the recipient.

    Args:
        recipient_label: Display label for the recipient (e.g., "@john" or "john")
    """
    lines = [
        "💬 Send anonymous message",
        "",
        f"Recipient: {recipient_label}",
        "",
        "Type your message below:",
        "(Max 1000 characters)",
        "",
        "Your message will be completely anonymous.",
    ]
    return "\n".join(lines)


# Notifications
def get_new_message_notification() -> str:
    """Notification text sent to recipient when a new message arrives."""
    return (
        "📬 You just received a new anonymous message!\n\n"
        "Open your Inbox to read it."
    )


# Inbox messages
def get_no_messages_message() -> str:
    """Shown when the inbox is empty."""
    return "📭 No messages yet! Share your link to receive messages."


def format_inbox_message(index: int, total: int, content: str) -> str:
    """Format the inbox view for a single message.

    Args:
        index: 0-based index in the list (newest first)
        total: total messages count
        content: message body
    """
    header = f"📬 INBOX (Message {index + 1} of {total})\n\n"
    body = f"💬 Anonymous message:\n\n{content}"
    return header + body