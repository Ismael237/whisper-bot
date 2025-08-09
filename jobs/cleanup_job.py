from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database.database import get_db_session
from database.models import UserSession
from utils.logger import logger
from utils.time_utils import get_utc_time
from config import CLEANUP_OLD_SESSIONS_HOURS


def _cleanup_expired_sessions() -> None:
    try:
        with get_db_session() as db:
            now = get_utc_time()
            deleted = (
                db.query(UserSession)
                .filter(UserSession.expires_at < now)
                .delete(synchronize_session=False)
            )
            db.flush()
            if deleted:
                logger.info(f"[CleanupJob] Deleted {deleted} expired sessions")
    except Exception as e:
        logger.warning(f"[CleanupJob] Failed to cleanup sessions: {e}")


def setup_cleanup_scheduler(scheduler: AsyncIOScheduler | None = None) -> AsyncIOScheduler:
    """Configure a periodic job to cleanup expired sessions."""
    sched = scheduler or AsyncIOScheduler()
    hours = float(CLEANUP_OLD_SESSIONS_HOURS or 24)
    sched.add_job(_cleanup_expired_sessions, IntervalTrigger(hours=hours), id="cleanup_sessions", replace_existing=True)
    return sched


