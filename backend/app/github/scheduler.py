"""The scheduled GitHub refresh, run as a background task in the lifespan.

A plain ``asyncio`` loop keeps the project free of a scheduler dependency. It
syncs on start and then every interval, each run offloaded to a thread so the
blocking httpx and sqlite calls never stall the event loop. A failed sync only
logs and keeps the existing cache, the loop survives. The interval is
``GITHUB_SYNC_INTERVAL_SECONDS`` (default six hours), and zero or less disables
the scheduled run, which keeps tests and local runs quiet.
"""

import asyncio
import logging
import os

from app.github.sync import sync_repos

logger = logging.getLogger("uvicorn.error")

DEFAULT_INTERVAL_SECONDS = 6 * 60 * 60


def _interval_seconds() -> float:
    raw = os.environ.get("GITHUB_SYNC_INTERVAL_SECONDS")
    if raw is None or raw == "":
        return float(DEFAULT_INTERVAL_SECONDS)
    try:
        return float(raw)
    except ValueError:
        return float(DEFAULT_INTERVAL_SECONDS)


async def _run_loop(interval: float) -> None:
    """Sync now and then every ``interval`` seconds, never crashing on error."""
    while True:
        try:
            count = await asyncio.to_thread(sync_repos)
            logger.info("github sync: %d repos refreshed", count)
        except Exception:
            # Any failure keeps the existing cache and the loop alive. The
            # token is never part of the message.
            logger.warning("github sync failed; keeping the existing cache")
        await asyncio.sleep(interval)


def start_scheduler() -> asyncio.Task | None:
    """Start the background refresh task, or ``None`` when disabled.

    Creating the task returns at once, so the first sync runs concurrently and
    never blocks app start.
    """
    interval = _interval_seconds()
    if interval <= 0:
        logger.info("github sync scheduler disabled (interval <= 0)")
        return None
    return asyncio.create_task(_run_loop(interval))
