import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.router import router
from app.database import engine
from app.providers.btc.kraken_ws import run_kraken_ws
from app.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def _wait_for_db(retries: int = 10, delay: float = 3.0) -> None:
    from sqlalchemy import text

    for attempt in range(1, retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database is reachable")
            return
        except Exception as exc:
            logger.warning("DB not ready (attempt %d/%d): %s", attempt, retries, exc)
            if attempt < retries:
                await asyncio.sleep(delay)
    raise RuntimeError("Database did not become reachable in time")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _wait_for_db()

    scheduler = setup_scheduler()
    scheduler.start()

    kraken_task = asyncio.create_task(run_kraken_ws())

    logger.info("Pricing service started")
    yield

    scheduler.shutdown(wait=False)
    kraken_task.cancel()
    with suppress(asyncio.CancelledError):
        await kraken_task
    await engine.dispose()
    logger.info("Pricing service stopped")


app = FastAPI(title="Pricing Service", version="0.1.0", lifespan=lifespan)
app.include_router(router)
