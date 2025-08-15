import logging
import time
from typing import Dict, Any, Optional
import yfinance as yf

from app.clients.base import BaseAPIClient

logger = logging.getLogger(__name__)


class YFinanceClient(BaseAPIClient):
    """Client for Yahoo Finance API"""
    
    def __init__(self, timeout: float = 10.0, rate_limit_delay: float = 1.0):
        super().__init__("YFinance", timeout)
        self.rate_limit_delay = rate_limit_delay
    
    async def get_ticker_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data from Yahoo Finance"""
        try:
            logger.debug(f"Fetching data from YFinance for {symbol}")
            
            # Add rate limiting delay
            time.sleep(self.rate_limit_delay)
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            
            if hist.empty:
                logger.warning(f"No historical data found for {symbol}")
                return None
            
            # Get the latest price data
            latest = hist.iloc[-1]
            price = float(latest["Close"])
            
            ticker_data = {
                "symbol": symbol,
                "price": price,
                "open": float(latest.get("Open", price)),
                "high": float(latest.get("High", price)),
                "low": float(latest.get("Low", price)),
                "volume": int(latest.get("Volume", 0)),
                "source": "yfinance"
            }
            
            logger.info(f"YFinance data retrieved successfully for {symbol}: ${price}")
            return ticker_data
            
        except Exception as e:
            self._handle_error(e, symbol, "data retrieval")
        
        return None
    
    async def get_ticker_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get full ticker information from Yahoo Finance"""
        try:
            logger.debug(f"Fetching full info from YFinance for {symbol}")
            
            # Add rate limiting delay
            time.sleep(self.rate_limit_delay)
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                logger.warning(f"No ticker info found for {symbol}")
                return None
            
            # Extract relevant information
            ticker_info = {
                "symbol": symbol,
                "long_name": info.get("longName", f"{symbol.upper()} Stock"),
                "industry": info.get("industry", "Unknown"),
                "sector": info.get("sector", "Unknown"),
                "market_cap": info.get("marketCap"),
                "employees": info.get("fullTimeEmployees"),
                "city": info.get("city"),
                "state": info.get("state"),
                "country": info.get("country"),
                "website": info.get("website"),
                "currentPrice": info.get("currentPrice"),
                "source": "yfinance_info"
            }
            
            logger.info(f"YFinance info retrieved successfully for {symbol}")
            return ticker_info
            
        except Exception as e:
            self._handle_error(e, symbol, "info retrieval")
        
        return None