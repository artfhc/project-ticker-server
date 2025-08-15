import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.clients.polygon import PolygonClient
from app.clients.coinbase import CoinbaseClient
from app.clients.yfinance import YFinanceClient
from app.services.cache import CacheService
from app.models.ticker import TickerPriceResponse, TickerInfoResponse
from app.core.exceptions import (
    DataSourceUnavailableError,
    TickerNotFoundError,
    ExternalAPIError
)

logger = logging.getLogger(__name__)


class TickerService:
    """Service for fetching and managing ticker data"""
    
    def __init__(
        self,
        cache_service: CacheService,
        polygon_api_key: Optional[str] = None,
        ticker_mapping: Optional[Dict[str, str]] = None
    ):
        self.cache = cache_service
        self.ticker_mapping = ticker_mapping or {}
        
        # Initialize API clients
        self.polygon_client = PolygonClient(polygon_api_key) if polygon_api_key else None
        self.coinbase_client = CoinbaseClient()
        self.yfinance_client = YFinanceClient()
        
        logger.info("TickerService initialized with clients: Polygon={}, Coinbase=Yes, YFinance=Yes".format(
            "Yes" if self.polygon_client else "No"
        ))
    
    def _resolve_symbol(self, ticker: str) -> str:
        """Resolve ticker symbol using mapping dictionary"""
        resolved = self.ticker_mapping.get(ticker.lower(), ticker)
        if resolved != ticker:
            logger.debug(f"Resolved ticker '{ticker}' to '{resolved}'")
        return resolved
    
    async def get_price_data(self, ticker: str) -> TickerPriceResponse:
        """Get price data for a ticker symbol"""
        symbol = self._resolve_symbol(ticker)
        cache_key = f"price_{symbol}"
        
        # Check cache first
        cached_data = self.cache.get(cache_key)
        if cached_data:
            logger.info(f"Using cached price data for {symbol}")
            return TickerPriceResponse(**cached_data)
        
        logger.info(f"Fetching fresh price data for {symbol}")
        
        # Try data sources in order of preference
        data_sources = self._get_price_data_sources(symbol)
        
        for source_name, source_func in data_sources:
            try:
                logger.debug(f"Trying {source_name} for {symbol}")
                data = await source_func(symbol)
                
                if data:
                    logger.info(f"Successfully retrieved price data for {symbol} from {source_name}")
                    
                    # Cache the successful result
                    self.cache.set(cache_key, data)
                    
                    return TickerPriceResponse(**data)
                    
            except ExternalAPIError as e:
                logger.warning(f"{source_name} failed for {symbol}: {e.message}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error with {source_name} for {symbol}: {e}")
                continue
        
        # All sources failed
        error_msg = f"Unable to fetch price data for symbol '{symbol}': All data sources unavailable"
        logger.error(error_msg)
        raise DataSourceUnavailableError(error_msg)
    
    async def get_full_info(self, ticker: str) -> TickerInfoResponse:
        """Get full ticker information"""
        symbol = self._resolve_symbol(ticker)
        cache_key = f"info_{symbol}"
        
        # Check cache first
        cached_data = self.cache.get(cache_key)
        if cached_data:
            logger.info(f"Using cached info data for {symbol}")
            return TickerInfoResponse(**cached_data)
        
        logger.info(f"Fetching fresh info data for {symbol}")
        
        # Get price data first
        try:
            price_response = await self.get_price_data(ticker)
            price_data = price_response.dict()
        except DataSourceUnavailableError:
            raise
        
        # Enhance with company/commodity information
        info_data = await self._enhance_with_info(symbol, price_data)
        
        # Cache the result
        self.cache.set(cache_key, info_data)
        
        return TickerInfoResponse(**info_data)
    
    def _get_price_data_sources(self, symbol: str) -> List[tuple]:
        """Get ordered list of data sources for price data"""
        sources = []
        
        # Special handling for gold (XAU)
        if symbol.upper() == 'XAU':
            sources.append(("Coinbase", self.coinbase_client.get_ticker_data))
        
        # Add Polygon if available
        if self.polygon_client:
            sources.append(("Polygon", self.polygon_client.get_ticker_data))
        
        # Always add YFinance as fallback
        sources.append(("YFinance", self.yfinance_client.get_ticker_data))
        
        return sources
    
    async def _enhance_with_info(self, symbol: str, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance price data with company/commodity information"""
        try:
            if symbol.upper() == 'XAU':
                # Special case for gold
                info_data = {
                    "long_name": "Gold Spot Price (XAU/USD)",
                    "industry": "Precious Metals",
                    "sector": "Commodities",
                    "market_cap": None,
                    "employees": None,
                    "city": "Global",
                    "state": "Global",
                    "country": "Global",
                    "website": "https://www.coinbase.com",
                    "commodity": "gold",
                    "currency_pair": "XAU/USD"
                }
            else:
                # Try to get company info from YFinance
                yf_info = await self.yfinance_client.get_ticker_info(symbol)
                if yf_info:
                    info_data = yf_info
                else:
                    # Basic fallback info
                    info_data = {
                        "long_name": f"{symbol.upper()} Stock",
                        "industry": "Unknown",
                        "sector": "Unknown",
                        "market_cap": None,
                        "employees": None,
                        "city": "Unknown",
                        "state": "Unknown",
                        "country": "Unknown",
                        "website": None
                    }
            
            # Combine price data with info
            combined_data = {
                **info_data,
                **price_data,
                "currentPrice": price_data["price"],
                "source": f"{price_data['source']}_with_info"
            }
            
            return combined_data
            
        except Exception as e:
            logger.warning(f"Failed to enhance data with info for {symbol}: {e}")
            # Return price data with basic info
            return {
                **price_data,
                "long_name": f"{symbol.upper()} Stock",
                "industry": "Unknown",
                "sector": "Unknown",
                "currentPrice": price_data["price"],
                "source": f"{price_data['source']}_basic_info"
            }
    
    def clear_cache(self) -> None:
        """Clear all cached ticker data"""
        try:
            self.cache_service.clear()
            logger.info("All ticker cache cleared")
        except Exception as e:
            logger.error(f"Error clearing ticker cache: {e}")
            raise
    
    async def close(self):
        """Close all API clients"""
        try:
            if self.polygon_client:
                await self.polygon_client.close()
            await self.coinbase_client.close()
            logger.info("TickerService clients closed")
        except Exception as e:
            logger.error(f"Error closing TickerService clients: {e}")