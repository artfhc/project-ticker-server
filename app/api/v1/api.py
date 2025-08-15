from fastapi import APIRouter

from .endpoints import users, tickers

router = APIRouter()
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(tickers.router, prefix="/tickers", tags=["Tickers"])
