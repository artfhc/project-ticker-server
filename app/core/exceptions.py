from typing import Optional


class TickerException(Exception):
    """Base exception for ticker-related errors"""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class TickerNotFoundError(TickerException):
    """Raised when a ticker symbol is not found"""
    pass


class DataSourceUnavailableError(TickerException):
    """Raised when all data sources are unavailable"""
    pass


class RateLimitError(TickerException):
    """Raised when API rate limits are exceeded"""
    pass


class InvalidTickerError(TickerException):
    """Raised when ticker symbol is invalid"""
    pass


class CacheError(TickerException):
    """Raised when cache operations fail"""
    pass


class ExternalAPIError(TickerException):
    """Raised when external API calls fail"""
    
    def __init__(self, message: str, source: str, detail: Optional[str] = None):
        self.source = source
        super().__init__(message, detail)