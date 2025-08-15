import logging
from typing import Dict, Any, Optional
import httpx

from app.clients.base import BaseAPIClient
from app.core.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)


class PolygonClient(BaseAPIClient):
    """Client for Polygon.io API"""
    
    def __init__(self, api_key: str, timeout: float = 10.0):
        super().__init__("Polygon.io", timeout)
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
        self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def get_ticker_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data from Polygon.io"""
        if not self.api_key:
            logger.warning("Polygon API key not provided")
            return None
        
        try:
            symbol_upper = symbol.upper()
            client = await self._get_client()
            
            url = f"{self.base_url}/v2/aggs/ticker/{symbol_upper}/prev"
            params = {'apikey': self.api_key}
            
            logger.debug(f"Fetching data from Polygon for {symbol_upper}")
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'OK' and data.get('results'):
                    result = data['results'][0]
                    ticker_data = {
                        "symbol": symbol_upper,
                        "price": float(result['c']),  # close price
                        "open": float(result['o']),   # open price
                        "high": float(result['h']),   # high price
                        "low": float(result['l']),    # low price
                        "volume": int(result['v']),   # volume
                        "source": f"polygon_{self.name.lower()}",
                        "timestamp": result.get('t', 0)
                    }
                    logger.info(f"Polygon data retrieved successfully for {symbol_upper}")
                    return ticker_data
                else:
                    logger.warning(f"No data found in Polygon response for {symbol_upper}")
            else:
                logger.warning(f"Polygon API returned status {response.status_code} for {symbol_upper}")
            
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