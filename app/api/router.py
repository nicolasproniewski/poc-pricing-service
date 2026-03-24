from fastapi import APIRouter

from app.api import btc, health, sofr

router = APIRouter(prefix="/v1")
router.include_router(btc.router)
router.include_router(sofr.router)
router.include_router(health.router)
