import logging
from fastapi import APIRouter, HTTPException, Depends, Path
from fastapi.responses import PlainTextResponse

from app.models.ticker import TickerPriceResponse, TickerInfoResponse, ErrorResponse, CacheClearResponse
from app.services.ticker import TickerService
from app.core.exceptions import (
    DataSourceUnavailableError,
    TickerNotFoundError,
    ExternalAPIError
)
from app.core.dependencies import get_ticker_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/price/{ticker}",
    response_model=TickerPriceResponse,
    summary="Get ticker price data",
    description="Get current price and trading data for a ticker symbol",
    responses={
        200: {"description": "Successful response", "model": TickerPriceResponse},
        404: {"description": "Ticker not found", "model": ErrorResponse},
        500: {"description": "Data source unavailable", "model": ErrorResponse},
        503: {"description": "Service unavailable", "model": ErrorResponse}
    }
)
async def get_ticker_price(
    ticker: str = Path(..., description="Ticker symbol", example="AAPL"),
    ticker_service: TickerService = Depends(get_ticker_service)
) -> TickerPriceResponse:
    """Get price data for a ticker symbol"""
    try:
        logger.info(f"Price request for ticker: {ticker}")
        return await ticker_service.get_price_data(ticker)
        
    except TickerNotFoundError as e:
        logger.warning(f"Ticker not found: {ticker}")
        raise HTTPException(status_code=404, detail=str(e))
        
    except DataSourceUnavailableError as e:
        logger.error(f"Data sources unavailable for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except ExternalAPIError as e:
        logger.error(f"External API error for {ticker}: {e}")
        raise HTTPException(status_code=503, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{ticker}",
    response_model=TickerInfoResponse,
    summary="Get full ticker information",
    description="Get comprehensive ticker information including price data and company details",
    responses={
        200: {"description": "Successful response", "model": TickerInfoResponse},
        404: {"description": "Ticker not found", "model": ErrorResponse},
        500: {"description": "Data source unavailable", "model": ErrorResponse},
        503: {"description": "Service unavailable", "model": ErrorResponse}
    }
)
async def get_ticker_info(
    ticker: str = Path(..., description="Ticker symbol", example="AAPL"),
    ticker_service: TickerService = Depends(get_ticker_service)
) -> TickerInfoResponse:
    """Get full information for a ticker symbol"""
    try:
        logger.info(f"Info request for ticker: {ticker}")
        return await ticker_service.get_full_info(ticker)
        
    except TickerNotFoundError as e:
        logger.warning(f"Ticker not found: {ticker}")
        raise HTTPException(status_code=404, detail=str(e))
        
    except DataSourceUnavailableError as e:
        logger.error(f"Data sources unavailable for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except ExternalAPIError as e:
        logger.error(f"External API error for {ticker}: {e}")
        raise HTTPException(status_code=503, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Backward compatibility endpoint for plain text price response
@router.get(
    "/price/{ticker}/plain",
    response_class=PlainTextResponse,
    summary="Get ticker price as plain text",
    description="Get current price as plain text (backward compatibility)",
    responses={
        200: {"description": "Price as plain text", "content": {"text/plain": {"example": "150.25"}}},
        404: {"description": "Ticker not found"},
        500: {"description": "Data source unavailable"}
    }
)
async def get_ticker_price_plain(
    ticker: str = Path(..., description="Ticker symbol", example="AAPL"),
    ticker_service: TickerService = Depends(get_ticker_service)
) -> str:
    """Get price as plain text for backward compatibility"""
    try:
        logger.info(f"Plain text price request for ticker: {ticker}")
        price_data = await ticker_service.get_price_data(ticker)
        return str(price_data.price)
        
    except TickerNotFoundError as e:
        logger.warning(f"Ticker not found: {ticker}")
        raise HTTPException(status_code=404, detail=str(e))
        
    except DataSourceUnavailableError as e:
        logger.error(f"Data sources unavailable for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/cache",
    response_model=CacheClearResponse,
    summary="Clear ticker cache",
    description="Clear all cached ticker data to force fresh data retrieval",
    responses={
        200: {"description": "Cache cleared successfully", "model": CacheClearResponse},
        500: {"description": "Failed to clear cache", "model": ErrorResponse}
    }
)
async def clear_cache(
    ticker_service: TickerService = Depends(get_ticker_service)
) -> CacheClearResponse:
    """Clear all cached ticker data"""
    try:
        logger.info("Cache clear request received")
        ticker_service.clear_cache()
        logger.info("Cache cleared successfully")
        return CacheClearResponse(
            message="Cache cleared successfully",
            cleared=True
        )
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")