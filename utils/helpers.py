from datetime import datetime, date, timezone
from functools import wraps
from typing import Any, Callable, TypeVar, Optional, Dict, Type, Tuple, Union
from typing_extensions import ParamSpec
import logging
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