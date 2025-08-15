import os
from functools import lru_cache
from app.services.ticker import TickerService
from app.services.cache import CacheService


# Ticker symbol mapping
TICKER_MAPPING = {
    'gold': 'XAU'  # Use XAU for real gold prices from Coinbase
}

# Cache service instance (singleton)
_cache_service = None
_ticker_service = None


@lru_cache()
def get_cache_service() -> CacheService:
    """Get or create cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(ttl_seconds=300)  # 5 minutes
    return _cache_service


@lru_cache()
def get_ticker_service() -> TickerService:
    """Get or create ticker service instance"""
    global _ticker_service
    if _ticker_service is None:
        cache_service = get_cache_service()
        polygon_api_key = os.getenv("POLYGON_API_KEY", "")
        
        _ticker_service = TickerService(
            cache_service=cache_service,
            polygon_api_key=polygon_api_key if polygon_api_key else None,
            ticker_mapping=TICKER_MAPPING
        )
    return _ticker_service