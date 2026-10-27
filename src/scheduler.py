
"""Simple in-process scheduler; no distributed orchestration framework."""
import logging
import time
from datetime import datetime
from .pipeline import run_pipeline

logger = logging.getLogger(__name__)

def run_schedule(mode="demo", interval_minutes=1440, limit=30):
    if interval_minutes < 1:
        raise ValueError("interval_minutes must be at least 1")
    interval_seconds = interval_minutes * 60
    logger.info("Scheduler started: mode=%s interval_minutes=%s", mode, interval_minutes)
    try:
        while True:
            started = time.monotonic()
            logger.info("Scheduled run starting at %s", datetime.now().isoformat(timespec="seconds"))
            try:
                result = run_pipeline(mode=mode, limit=limit)
                logger.info("Scheduled run finished: %s", result["status"])
            except Exception:
                logger.exception("Scheduled pipeline run failed")
            elapsed = time.monotonic() - started
            time.sleep(max(0, interval_seconds - elapsed))
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
