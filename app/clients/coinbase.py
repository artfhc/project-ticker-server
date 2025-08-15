import logging
from typing import Dict, Any, Optional
import httpx

from app.clients.base import BaseAPIClient

logger = logging.getLogger(__name__)


class CoinbaseClient(BaseAPIClient):
    """Client for Coinbase API (primarily for gold prices)"""
    
    def __init__(self, timeout: float = 10.0):
        super().__init__("Coinbase", timeout)
        self.base_url = "https://api.coinbase.com/v2"
        self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def get_ticker_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data from Coinbase (only supports XAU/gold currently)"""
        if symbol.upper() != 'XAU':
            logger.debug(f"Coinbase client only supports XAU, got: {symbol}")
            return None
        
        try:
            client = await self._get_client()
            
            # Coinbase public API for XAU-USD (gold spot price)
            url = f"{self.base_url}/exchange-rates?currency=XAU"
            
            logger.debug("Fetching gold price from Coinbase")
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                rates = data.get('data', {}).get('rates', {})
                usd_rate = rates.get('USD')
                
                if usd_rate:
                    price = float(usd_rate)
                    ticker_data = {
                        "symbol": "XAU",
                        "price": price,
                        "open": price,  # Coinbase doesn't provide OHLC for spot rates
                        "high": price,
                        "low": price,
                        "volume": 0,
                        "source": "coinbase_gold",
                        "currency": "USD",
                        "commodity": "gold"
                    }
                    logger.info(f"Coinbase gold data retrieved successfully: ${price}")
                    return ticker_data
                else:
                    logger.warning("No USD rate found in Coinbase response")
            else:
                logger.warning(f"Coinbase API returned status {response.status_code}")
                
        except httpx.TimeoutException:
            self._handle_error(Exception("Request timeout"), symbol, "API call")
        except httpx.RequestError as e:
            self._handle_error(e, symbol, "API request")
        except Exception as e:
            self._handle_error(e, symbol, "data retrieval")
        
        return None
    
    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None