"""
Scheduler — auto-fetch daily limit-up data at market close.

Usage:
    python -m cn_stock.scheduler

Registers one cron job: 15:30 every weekday (Mon-Fri).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from cn_stock.pipeline import fetch_latest
from cn_stock.tagging import needs_llm

logger = logging.getLogger("cn_stock.scheduler")


def start_scheduler() -> BackgroundScheduler:
    """Start the daily fetch scheduler. Returns scheduler instance."""
    scheduler = BackgroundScheduler()

    use_llm = needs_llm()
    logger.info(f"LLM tagging: {'enabled' if use_llm else 'disabled (no API key)'}")

    scheduler.add_job(
        lambda: _run(use_llm),
        "cron",
        day_of_week="mon-fri",
        hour=15,
        minute=37,  # 15:37 — avoid :00/:30 contention
        id="cn_stock_daily_fetch",
        name="CN Stock daily limit-up fetch (15:37 Mon-Fri)",
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info("CN Stock scheduler started — daily fetch at 15:37 Mon-Fri")
    return scheduler


def _run(use_llm: bool) -> None:
    logger.info(f"Running daily fetch (LLM={use_llm})...")
    start = time.time()
    result = fetch_latest(use_llm=use_llm)
    elapsed = time.time() - start
    logger.info(f"Daily fetch done in {elapsed:.1f}s — {result}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    scheduler = start_scheduler()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
