#!/usr/bin/env python
"""Parser service: sync SPbPU RUZ schedules into bookings (source=RUZ)."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from config import RUZ_SYNC_INTERVAL_SECONDS, RUZ_SYNC_WEEKS, SERVICE_NAME, SERVICE_PORT
from sync import is_sync_running, last_sync_result, run_sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

_stop_periodic = threading.Event()


def _periodic_sync_loop() -> None:
    """Background loop: sync on startup, then every RUZ_SYNC_INTERVAL_SECONDS."""
    # Small delay so Postgres is ready when started via compose.
    if _stop_periodic.wait(5):
        return
    logger.info("Initial RUZ sync starting")
    try:
        run_sync()
    except Exception:  # noqa: BLE001
        logger.exception("Initial RUZ sync crashed")

    while not _stop_periodic.wait(max(60, RUZ_SYNC_INTERVAL_SECONDS)):
        logger.info("Scheduled RUZ sync starting")
        try:
            run_sync()
        except Exception:  # noqa: BLE001
            logger.exception("Scheduled RUZ sync crashed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    thread = threading.Thread(target=_periodic_sync_loop, name="ruz-sync", daemon=True)
    if RUZ_SYNC_INTERVAL_SECONDS > 0:
        thread.start()
        logger.info("Periodic RUZ sync enabled every %ss", RUZ_SYNC_INTERVAL_SECONDS)
    else:
        logger.info("Periodic RUZ sync disabled (RUZ_SYNC_INTERVAL_SECONDS<=0)")
    yield
    _stop_periodic.set()


app = FastAPI(title=SERVICE_NAME, lifespan=lifespan)


class SyncRequest(BaseModel):
    weeks: int | None = Field(default=None, ge=1, le=8, description="How many weeks ahead to sync")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "sync_running": is_sync_running(),
        "last_sync": last_sync_result(),
    }


@app.get("/sync")
def sync_status() -> dict[str, Any]:
    return {
        "running": is_sync_running(),
        "last": last_sync_result(),
    }


@app.post("/sync")
def trigger_sync(
    background_tasks: BackgroundTasks,
    body: SyncRequest | None = None,
) -> dict[str, Any]:
    """Trigger a RUZ → bookings sync in the background."""
    if is_sync_running():
        raise HTTPException(409, "Sync already running")
    weeks = body.weeks if body else None

    def _job() -> None:
        run_sync(weeks=weeks)

    background_tasks.add_task(_job)
    return {"status": "started", "weeks": weeks or RUZ_SYNC_WEEKS}


@app.post("/sync/run")
def trigger_sync_inline(body: SyncRequest | None = None) -> dict[str, Any]:
    """Run sync in-request (useful for local debugging; may take minutes)."""
    if is_sync_running():
        raise HTTPException(409, "Sync already running")
    weeks = body.weeks if body else None
    return run_sync(weeks=weeks)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=SERVICE_PORT, reload=False)
