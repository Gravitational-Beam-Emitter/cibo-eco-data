"""
APScheduler — daily Korean stock data fetch at 16:07 KST (Mon-Fri).

Usage:
    python -m kr_stock.scheduler
"""

from __future__ import annotations

import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("kr_stock.scheduler")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")

    scheduler.add_job(
        _run,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=16,
            minute=7,  # Avoid :00/:30 congestion
            timezone="Asia/Seoul",
        ),
        misfire_grace_time=3600,
        id="kr_stock_daily_fetch",
        replace_existing=True,
    )

    logger.info("KR Stock scheduler registered: Mon-Fri 16:07 KST")
    return scheduler


def _run() -> None:
    from kr_stock.pipeline import fetch_latest

    start = time.monotonic()
    try:
        result = fetch_latest(use_llm=True)
        elapsed = time.monotonic() - start
        logger.info(f"Daily fetch completed in {elapsed:.1f}s: {result}")
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error(f"Daily fetch FAILED after {elapsed:.1f}s: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    scheduler = start_scheduler()
    scheduler.start()
    logger.info("KR Stock scheduler running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")
