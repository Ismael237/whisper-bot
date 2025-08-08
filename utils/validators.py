from __future__ import annotations

import re
from typing import Tuple

from config import MIN_USERNAME_LENGTH, MAX_USERNAME_LENGTH, MAX_MESSAGE_LENGTH


USERNAME_REGEX = re.compile(r"^[A-Za-z0-9_]+$")


def normalize_username(username: str | None) -> str | None:
    """Trim and normalize username casing if needed (keep original case).

    Returns the stripped value.
    """
    if username is None:
        raise ValueError("Username cannot be None")
    return username.strip().lower()


def validate_username(username: str | None) -> Tuple[bool, str | None]:
    """Validate username format and length constraints.

    - Allowed: letters, digits, underscore
    - Length: MIN_USERNAME_LENGTH..MAX_USERNAME_LENGTH
    """
    try:
        min_len = int(MIN_USERNAME_LENGTH)
        max_len = int(MAX_USERNAME_LENGTH)
    except Exception:
        min_len, max_len = 3, 20

    if not username:
        return False, "Username is required"

    value = normalize_username(username)
    if len(value) < min_len:
        return False, f"Username must be at least {min_len} characters"
    if len(value) > max_len:
        return False, f"Username must be at most {max_len} characters"
    if not USERNAME_REGEX.match(value):
        return False, "Username may contain only letters, digits and underscores"
    return True, value


def validate_message_length(content: str | None) -> Tuple[bool, str]:
    """Validate anonymous message length boundaries against MAX_MESSAGE_LENGTH."""
    try:
        max_len = int(MAX_MESSAGE_LENGTH)
    except Exception:
        max_len = 1000

    if content is None:
        return False, "Message cannot be None"

    text = content.strip()
    if len(text) == 0:
        return False, "Message cannot be empty"
    if len(text) > max_len:
        return False, f"Message exceeds maximum length of {max_len} characters"
    return True, text


