from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from services.stats_service import get_global_stats
from utils.logger import logger


def _recompute_daily_stats() -> None:
    try:
        stats = get_global_stats()
        logger.info(f"[StatsJob] Daily stats recomputed: {stats}")
    except Exception as e:
        logger.warning(f"[StatsJob] Failed to recompute daily stats: {e}")


def setup_stats_scheduler(scheduler: AsyncIOScheduler | None = None) -> AsyncIOScheduler:
    """Configure a daily job to recompute global stats."""
    sched = scheduler or AsyncIOScheduler()
    sched.add_job(_recompute_daily_stats, CronTrigger(hour=0, minute=5), id="daily_stats", replace_existing=True)
    return sched


