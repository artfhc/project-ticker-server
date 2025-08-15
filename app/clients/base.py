import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from app.core.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)


class BaseAPIClient(ABC):
    """Base class for external API clients"""
    
    def __init__(self, name: str, timeout: float = 10.0):
        self.name = name
        self.timeout = timeout
        logger.info(f"Initialized {name} client with timeout: {timeout}s")
    
    @abstractmethod
    async def get_ticker_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data from the external API"""
        pass
    
    def _handle_error(self, error: Exception, symbol: str, operation: str) -> None:
        """Standard error handling for API clients"""
        error_msg = f"{self.name} {operation} failed for {symbol}: {str(error)}"
        logger.error(error_msg)
        raise ExternalAPIError(
            message=f"{operation} failed",
            source=self.name,
            detail=str(error)
        )