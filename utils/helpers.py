from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from database.models import SessionType
from datetime import datetime, date, timezone
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, Optional, Dict, Type, Tuple, Union
from typing_extensions import ParamSpec
import logging
import time
import re

# Type variables for generic function typing
T = TypeVar('T')
P = ParamSpec('P')
R = TypeVar('R')

def generate_share_link(bot_username: str, code: str) -> str:
    """Generate a Telegram share link with the given bot username and start code.
    
    Args:
        bot_username: The bot's username without the @ symbol
        code: The start parameter to include in the link
        
    Returns:
        str: The complete Telegram share URL
    """
    if not bot_username or not code:
        raise ValueError("bot_username and code are required")
    return f"https://t.me/{bot_username.lstrip('@')}?start={code}"

def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2 formatting.
    
    Args:
        text: The text to escape
        
    Returns:
        str: The escaped text
    """
    escape_chars = r'\\`*_\[\]()~>#+=|{}.!-'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def get_utc_time() -> datetime:
    """Get current UTC time with timezone info.
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)

def get_utc_date() -> date:
    """Get current UTC date.
    
    Returns:
        date: Current UTC date
    """
    return get_utc_time().date()

def get_separator(length: int = 20) -> str:
    """Get a separator line of specified length.
    
    Args:
        length: Length of the separator
        
    Returns:
        str: Separator string
    """
    return "─" * max(1, int(length))

def retry(
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    logger: Optional[logging.Logger] = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry decorator with exponential backoff.
    
    Args:
        exceptions: Exception(s) to catch and retry on
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay between retries
        logger: Logger instance for logging retries
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        break
                        
                    if logger is not None:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {str(e)}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                    
                    time.sleep(delay)
                    delay *= backoff_factor
            
            raise last_exception  # type: ignore
        
        return wrapper
    return decorator

def safe_get(dictionary: Dict[Any, Any], *keys: Any, default: Any = None) -> Any:
    """Safely get a value from nested dictionaries.
    
    Args:
        dictionary: The dictionary to search in
        *keys: Keys to traverse the dictionary
        default: Default value if key not found
        
    Returns:
        The value if found, otherwise default
    """
    current = dictionary
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def require_session_step(session_type: SessionType, step: str) -> Callable[[Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]], Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]]:
    """Decorator for handlers to require a specific session step.

    If the condition is not met, the wrapped handler is skipped (returns early).
    """

    def decorator(func: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            tg_user = update.effective_user if hasattr(update, "effective_user") else None
            if not tg_user:
                return
            # Lazy import to avoid circular import at module load time
            from services.session_service import get_active_session
            sess = get_active_session(tg_user.id, session_type)
            if not sess or (sess.current_step or "") != step:
                return
            return await func(update, context)

        return wrapper

    return decorator


async def advance_step(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    session_type: SessionType,
    next_step: str | None,
) -> None:
    """Advance the current_step of a user's session to the next step (or clear)."""
    from services.session_service import set_current_step

    tg_user = update.effective_user if hasattr(update, "effective_user") else None
    if not tg_user:
        return
    set_current_step(tg_user.id, session_type, next_step)
