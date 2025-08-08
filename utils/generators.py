from __future__ import annotations

import secrets
import string
from typing import Iterator


ALPHANUMERIC = string.ascii_uppercase + string.digits


def generate_random_alphanumeric(length: int = 8) -> str:
    """Generate a cryptographically secure alphanumeric string.

    Args:
        length: Desired length of the random part

    Returns:
        Random alphanumeric string
    """
    length = max(1, int(length))
    return "".join(secrets.choice(ALPHANUMERIC) for _ in range(length))


def build_unique_code(username_part: str, random_length: int = 4) -> str:
    """Build a unique_code value in the format 'usernameXXXX' (no underscore).

    The caller is responsible for providing a username_part that already
    conforms to allowed characters (A-Z, a-z, 0-9, _).

    Args:
        username_part: Normalized username part to embed in the code
        random_length: Length of the random suffix

    Returns:
        A code like 'johnabcd' (with 4-char uppercase/digits suffix)
    """
    random_part = generate_random_alphanumeric(random_length)
    return f"{username_part}{random_part}"


def generate_candidate_codes(username_part: str, random_length: int = 4, max_attempts: int = 20) -> Iterator[str]:
    """Yield candidate unique codes for collision handling.

    Args:
        username_part: Normalized username part
        random_length: Suffix length
        max_attempts: Number of candidates to yield

    Yields:
        Candidate codes following the required format
    """
    attempts = max(1, int(max_attempts))
    for _ in range(attempts):
        yield build_unique_code(username_part, random_length)


