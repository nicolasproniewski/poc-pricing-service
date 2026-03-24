from fastapi import APIRouter
from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.providers.btc.kraken_ws import kraken_ws_status
from app.scheduler import scheduler

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    # DB check
    db_status = "connected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    scheduler_status = "running" if scheduler.running else "stopped"

    return {
        "status": "ok",
        "db": db_status,
        "kraken_ws": kraken_ws_status(),
        "scheduler": scheduler_status,
    }
