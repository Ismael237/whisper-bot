from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session as OrmSession

from config import BOT_USERNAME
from database.database import get_db_session
from database.models import User
from utils.generators import generate_candidate_codes
from utils.helpers import generate_share_link
from utils.logger import logger
from utils.validators import validate_username


@dataclass
class LinkResult:
    user: User
    link: str
    code: str
    created: bool


def _is_code_available(db: OrmSession, code: str) -> bool:
    return db.query(User).filter(User.unique_code == code).first() is None


def _ensure_unique_code(db: OrmSession, username_part: str) -> str:
    for candidate in generate_candidate_codes(username_part=username_part, random_length=4, max_attempts=50):
        if _is_code_available(db, candidate):
            return candidate
    raise RuntimeError("Failed to generate a unique link code without collisions")


def generate_or_get_link(
    telegram_id: int,
    desired_username: Optional[str] = None,
    *,
    session: Optional[OrmSession] = None,
) -> LinkResult:
    """Generate (or retrieve) the unique link for a user.

    - Validates the desired username if provided and updates the user display name
    - Generates a unique `unique_code` if still pending
    - Returns the t.me share link using BOT_USERNAME and the code
    """

    def _op(db: OrmSession) -> LinkResult:
        user = User.get_by_telegram_id(db, telegram_id)
        if user is None:
            raise ValueError("User not found. Ensure registration flow has run.")

        # Optionally validate and update display username
        if desired_username:
            ok, value_or_err = validate_username(desired_username)
            if not ok:
                raise ValueError(value_or_err)
            if user.username != value_or_err:
                user.username = value_or_err
                db.add(user)

        # If unique_code is a placeholder or empty, generate a proper one
        created = False
        if not user.unique_code or str(user.unique_code).startswith("pending-"):
            username_part = user.username
            code = _ensure_unique_code(db, username_part)
            user.unique_code = code
            db.add(user)
            created = True
        else:
            code = user.unique_code

        db.flush()

        link = generate_share_link(BOT_USERNAME, code)
        logger.info(f"[LinkService] Link ready for telegram_id={telegram_id} code={code}")
        return LinkResult(user=user, link=link, code=code, created=created)

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def validate_start_parameter(param: str) -> Optional[str]:
    """Validate an incoming /start parameter and return the code if valid.

    For MVP we accept the parameter as the `unique_code` value format
    'usernameXXXX' (no underscore). We only perform a basic sanity check here; full lookup
    should be done by fetching the user by unique_code where needed.
    """
    if not param:
        return None
    # Very basic shape check: username prefix + 4-char suffix
    if len(param) < 5:
        return None
    return param


