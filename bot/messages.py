
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
    'rate_limit': "⏳ Please wait before sending another message."
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
