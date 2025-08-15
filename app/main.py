import os
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from app.api.v1.api import router as api_router
from app.core.logging import setup_logging, get_logger
from app.core.dependencies import get_ticker_service
from app.core.exceptions import DataSourceUnavailableError
from app.models.ticker import HealthResponse
from app.services.ticker import TickerService

# Load environment variables
load_dotenv()

# Setup logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Ticker API application")
    
    # Startup
    polygon_api_key = os.getenv("POLYGON_API_KEY", "")
    logger.info(f"Loaded API keys: Polygon={'Yes' if polygon_api_key else 'No'}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Ticker API application")
    try:
        ticker_service = get_ticker_service()
        await ticker_service.close()
        logger.info("Services closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="Ticker API",
    description="A FastAPI application for fetching ticker/stock price data",
    version="2.0.0",
    lifespan=lifespan
)

@app.get("/", summary="Root endpoint")
def read_root():
    """Root endpoint returning a simple greeting"""
    return {"message": "Welcome to Ticker API v2.0", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, summary="Health check")
def health_check() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="2.0.0"
    )


# Backward compatibility endpoints (redirecting to new API structure)
@app.get("/ticker/price/{ticker}", response_class=PlainTextResponse, 
         deprecated=True, summary="Legacy price endpoint")
async def legacy_ticker_price(
    ticker: str,
    ticker_service: TickerService = Depends(get_ticker_service)
) -> str:
    """Legacy endpoint for ticker price (plain text response)"""
    logger.warning(f"Using deprecated endpoint /ticker/price/{ticker}. Use /api/v1/tickers/price/{ticker}/plain instead.")
    try:
        price_data = await ticker_service.get_price_data(ticker)
        return str(price_data.price)
    except DataSourceUnavailableError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error in legacy endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/ticker/{ticker}", deprecated=True, summary="Legacy info endpoint")
async def legacy_ticker_info(
    ticker: str,
    ticker_service: TickerService = Depends(get_ticker_service)
):
    """Legacy endpoint for ticker information"""
    logger.warning(f"Using deprecated endpoint /ticker/{ticker}. Use /api/v1/tickers/{ticker} instead.")
    try:
        info_data = await ticker_service.get_full_info(ticker)
        # Convert to dict for backward compatibility
        return info_data.dict(by_alias=True)
    except DataSourceUnavailableError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error in legacy endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Include API routers
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)