from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session as OrmSession

from config import MIN_USERNAME_LENGTH, MAX_USERNAME_LENGTH
from database.models import User, ActivityLog, ActionType
from database.database import get_db_session
from utils.helpers import get_utc_time
from utils.logger import logger


@dataclass
class UserSyncResult:
    """Result object for ensure_user call."""
    user: User
    created: bool


class UsernameValidationError(ValueError):
    """Raised when the provided username does not pass validation rules."""


def _validate_display_name(display_name: str | None) -> str:
    """Validate and normalize a non-unique display name for gameplay.

    The MVP rules allow any non-empty string with length constraints.

    Args:
        display_name: The user-facing display name to validate

    Returns:
        The normalized display name

    Raises:
        UsernameValidationError: If validation fails
    """
    if display_name is None:
        raise UsernameValidationError("Display name cannot be None")

    normalized = display_name.strip()
    try:
        min_len = int(MIN_USERNAME_LENGTH)
        max_len = int(MAX_USERNAME_LENGTH)
    except Exception:
        min_len = 3
        max_len = 20

    if len(normalized) < min_len:
        raise UsernameValidationError(
            f"Display name must be at least {min_len} characters"
        )
    if len(normalized) > max_len:
        raise UsernameValidationError(
            f"Display name must be at most {max_len} characters"
        )
    return normalized


def ensure_user(
    telegram_id: int,
    telegram_username: Optional[str],
    default_display_name: Optional[str] = None,
    *,
    is_active: bool = False,
    extra_details: Optional[Dict[str, Any]] = None,
    session: Optional[OrmSession] = None,
) -> UserSyncResult:
    """Ensure a `User` exists for the given Telegram identity.

    - Create on first `/start` with `is_active=False` (passive profile)
    - Always sync `telegram_username` if provided
    - If no display name is set yet, initialize it from `default_display_name` or
      fallback to `telegram_username` or `"Player"`.

    Note: `unique_code` is not generated at this stage (Feature 1.4).

    Args:
        telegram_id: Telegram numeric identifier
        telegram_username: Optional Telegram @username
        default_display_name: Optional initial display name for gameplay
        is_active: Whether the created user should be active (defaults to False)
        extra_details: Optional details to log into `ActivityLog`
        session: Optional SQLAlchemy session; if omitted a managed session is used

    Returns:
        UserSyncResult indicating the user instance and if it was created
    """

    def _op(db: OrmSession) -> UserSyncResult:
        created = False
        user = User.get_by_telegram_id(db, telegram_id)
        if user is None:
            # Prefer provided name; ensure it passes constraints
            base_name = default_display_name or telegram_username or f"Player-{telegram_id}"
            candidate = _validate_display_name(str(base_name))

            # Ensure uniqueness due to current DB unique index on lower(username)
            # Even though product spec allows non-unique names, schema enforces unique for now.
            # No uniqueness required anymore on username; keep as-is

            # Since models require unique_code non-null, set a placeholder for now;
            # true unique_code will be generated in Feature 2
            placeholder_code = f"pending-{telegram_id}"

            user = User(
                telegram_id=telegram_id,
                username=candidate,
                telegram_username=(f"@{telegram_username}" if telegram_username and not str(telegram_username).startswith("@") else telegram_username),
                unique_code=placeholder_code,
                is_active=is_active,
                created_at=get_utc_time(),
                updated_at=get_utc_time(),
                last_activity=get_utc_time(),
            )
            db.add(user)
            created = True
            logger.info(
                "[UserService] Created new user telegram_id={} username={}"
                .format(telegram_id, user.username),
            )
        else:
            # Sync telegram username always
            normalized_t_username = (
                f"@{telegram_username}" if telegram_username and not str(telegram_username).startswith("@") else telegram_username
            )
            if normalized_t_username != user.telegram_username:
                user.telegram_username = normalized_t_username
            user.update_activity(db)
            logger.info(f"[UserService] Synced user telegram_id={telegram_id}")

        # Log registration/start action
        try:
            ActivityLog.log_activity(
                db,
                telegram_id=telegram_id,
                action_type=ActionType.REGISTER if created else ActionType.LOGIN,
                details={"created": created, **(extra_details or {})},
            )
        except Exception as log_ex:
            logger.warning(f"[UserService] Failed to write activity log: {log_ex}")

        db.flush()
        return UserSyncResult(user=user, created=created)

    if session is not None:
        return _op(session)
    # Managed transaction scope
    with get_db_session() as db:
        return _op(db)


def update_display_name(
    telegram_id: int,
    new_display_name: str,
    *,
    session: Optional[OrmSession] = None,
) -> User:
    """Update the gameplay display name (non-unique) for a user.

    Args:
        telegram_id: Telegram numeric identifier
        new_display_name: New display name to apply
        session: Optional SQLAlchemy session; if omitted a managed session is used

    Returns:
        Updated `User` instance
    """
    normalized = _validate_display_name(new_display_name)

    def _op(db: OrmSession) -> User:
        user = User.get_by_telegram_id(db, telegram_id)
        if user is None:
            raise ValueError("User not found")
        user.username = normalized
        user.updated_at = get_utc_time()
        db.add(user)
        ActivityLog.log_activity(
            db,
            telegram_id=telegram_id,
            action_type=ActionType.REGISTER,
            details={"event": "update_display_name"},
        )
        db.flush()
        logger.info(f"[UserService] Updated display name telegram_id={telegram_id}")
        return user

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def set_active_status(
    telegram_id: int,
    active: bool,
    *,
    session: Optional[OrmSession] = None,
) -> User:
    """Activate or deactivate a user account.

    Args:
        telegram_id: Telegram numeric identifier
        active: Desired active flag
        session: Optional SQLAlchemy session; if omitted a managed session is used

    Returns:
        Updated `User` instance
    """

    def _op(db: OrmSession) -> User:
        user = User.get_by_telegram_id(db, telegram_id)
        if user is None:
            raise ValueError("User not found")
        user.is_active = active
        user.updated_at = get_utc_time()
        db.add(user)
        ActivityLog.log_activity(
            db,
            telegram_id=telegram_id,
            action_type=ActionType.LOGIN if active else ActionType.LOGOUT,
            details={"event": "set_active_status", "active": active},
        )
        db.flush()
        logger.info(f"[UserService] Set active status={active} telegram_id={telegram_id}")
        return user

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


def get_user_by_telegram_id(telegram_id: int, *, session: Optional[OrmSession] = None) -> Optional[User]:
    """Fetch a user by Telegram identifier.

    Args:
        telegram_id: Telegram numeric identifier
        session: Optional SQLAlchemy session; if omitted a managed session is used

    Returns:
        The `User` or None
    """

    def _op(db: OrmSession) -> Optional[User]:
        return User.get_by_telegram_id(db, telegram_id)

    if session is not None:
        return _op(session)
    with get_db_session() as db:
        return _op(db)


