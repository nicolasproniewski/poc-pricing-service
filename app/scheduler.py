import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.services import btc_service, sofr_service

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_scheduler() -> AsyncIOScheduler:
    if settings.btc_poll_interval_minutes > 0:
        scheduler.add_job(
            btc_service.fetch_and_store,
            trigger=IntervalTrigger(minutes=settings.btc_poll_interval_minutes),
            id="btc_fetch",
            replace_existing=True,
            misfire_grace_time=30,
        )
        logger.info("BTC polling every %d min", settings.btc_poll_interval_minutes)
    else:
        logger.info("BTC polling disabled (BTC_POLL_INTERVAL_MINUTES=0)")
    scheduler.add_job(
        sofr_service.fetch_and_store,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=8,
            minute=15,
            timezone="America/New_York",
        ),
        id="sofr_fetch",
        replace_existing=True,
    )
    logger.info("Scheduler configured: btc_fetch (1min), sofr_fetch (weekdays 08:15 ET)")
    return scheduler
