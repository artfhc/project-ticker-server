from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
import yfinance as yf
import uvicorn
from datetime import datetime, timedelta
import requests
import time
import httpx
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from app.api.v1.api import router as api_router

# Load environment variables from .env file
load_dotenv()

# API Keys - Load from environment variables
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")

print(f"Loaded API keys: Polygon={'Yes' if POLYGON_API_KEY else 'No'}")
print(f"DEBUG: Polygon API key = '{POLYGON_API_KEY}' (length: {len(POLYGON_API_KEY)})")

###############################################################################
#   Application object                                                        #
###############################################################################
app = FastAPI()

###############################################################################
#   Routers configuration                                                     #
###############################################################################

ticker_dict = {
    'gold': 'XAU'  # Use XAU for real gold prices from Coinbase
}

# Simple in-memory cache
cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 300  # 5 minutes

def is_cache_valid(cache_entry: Dict[str, Any]) -> bool:
    """Check if cache entry is still valid"""
    if not cache_entry:
        return False
    cache_time = cache_entry.get('timestamp')
    if not cache_time:
        return False
    return datetime.utcnow() - cache_time < timedelta(seconds=CACHE_TTL)

def get_from_cache(key: str) -> Any:
    """Get data from cache if valid"""
    cache_entry = cache.get(key)
    if cache_entry and is_cache_valid(cache_entry):
        return cache_entry['data']
    return None

def set_cache(key: str, data: Any):
    """Set data in cache with timestamp"""
    cache[key] = {
        'data': data,
        'timestamp': datetime.utcnow()
    }

def get_ticker_info_safe(ticker_symbol: str):
    """Safely fetch ticker info with error handling for rate limits"""
    try:
        ticker_info = yf.Ticker(ticker_symbol)
        # Add a small delay to help with rate limiting
        time.sleep(1.0)  # Increase delay for better rate limiting
        return ticker_info
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unable to fetch ticker data: {str(e)}")




async def get_polygon_real_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Get real data from Polygon.io with API key"""
    if not POLYGON_API_KEY:
        return None
        
    try:
        # Polygon.io requires uppercase symbols
        symbol_upper = symbol.upper()
        
        async with httpx.AsyncClient() as client:
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol_upper}/prev"
            params = {
                'apikey': POLYGON_API_KEY
            }
            
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'OK' and data.get('results'):
                    result = data['results'][0]
                    return {
                        "symbol": symbol_upper,  # Return uppercase symbol
                        "price": float(result['c']),    # close price
                        "open": float(result['o']),     # open price  
                        "high": float(result['h']),     # high price
                        "low": float(result['l']),      # low price
                        "volume": int(result['v']),     # volume
                        "source": "polygon_real",
                        "timestamp": result.get('t', 0)
                    }
                    
    except Exception as e:
        print(f"Polygon real API failed for {symbol}: {e}")
    
    return None




async def get_coinbase_gold_price() -> Optional[Dict[str, Any]]:
    """Get real gold price from Coinbase API"""
    try:
        async with httpx.AsyncClient() as client:
            # Coinbase public API for XAU-USD (gold spot price)
            url = "https://api.coinbase.com/v2/exchange-rates?currency=XAU"
            response = await client.get(url, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                rates = data.get('data', {}).get('rates', {})
                usd_rate = rates.get('USD')
                
                if usd_rate:
                    price = float(usd_rate)
                    return {
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
    except Exception as e:
        print(f"Coinbase gold API failed: {e}")
    return None


def get_price(symbol):
    """Simple yfinance price getter"""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1d")
    if hist.empty:
        return None
    return hist["Close"].iloc[-1]

def get_ticker_price_data(ticker_symbol: str):
    """Get price data with special handling for gold and Polygon.io primary, yfinance secondary"""
    cache_key = f"price_{ticker_symbol}"
    
    # Check cache first
    cached_data = get_from_cache(cache_key)
    if cached_data:
        print(f"Using cached data for {ticker_symbol}, source: {cached_data.get('source', 'unknown')}")
        return cached_data
    
    print(f"Fetching fresh data for {ticker_symbol}...")
    
    import asyncio
    
    # Special case: Handle XAU (gold) with Coinbase API
    if ticker_symbol.upper() == 'XAU':
        try:
            print(f"Attempting Coinbase gold API for {ticker_symbol}")
            gold_data = asyncio.run(get_coinbase_gold_price())
            if gold_data:
                print(f"Coinbase gold success for {ticker_symbol}: ${gold_data['price']}")
                set_cache(cache_key, gold_data)
                return gold_data
        except Exception as e:
            print(f"Coinbase gold API failed for {ticker_symbol}: {e}")
    
    # Primary: Try Polygon.io (if API key available)
    try:
        print(f"Attempting Polygon.io for {ticker_symbol}")
        polygon_data = asyncio.run(get_polygon_real_data(ticker_symbol))
        if polygon_data:
            print(f"Polygon.io success for {ticker_symbol}: ${polygon_data['price']}")
            set_cache(cache_key, polygon_data)
            return polygon_data
    except Exception as e:
        print(f"Polygon.io failed for {ticker_symbol}: {e}")
    
    # Secondary: Try simple yfinance approach  
    try:
        print(f"Attempting yfinance fallback for {ticker_symbol}")
        price = get_price(ticker_symbol)
        
        if price is not None:
            data = {
                "symbol": ticker_symbol,
                "price": float(price),
                "source": "yfinance_fallback"
            }
            print(f"yfinance fallback success for {ticker_symbol}: ${data['price']}")
            set_cache(cache_key, data)
            return data
        else:
            print(f"yfinance returned None for {ticker_symbol}")
            
    except Exception as e:
        print(f"yfinance fallback failed for {ticker_symbol}: {e}")
    
    # No data available - return error
    print(f"ERROR: All data sources failed for {ticker_symbol}")
    raise HTTPException(
        status_code=500, 
        detail=f"Unable to fetch data for symbol '{ticker_symbol}': All data sources unavailable"
    )


def get_ticker_full_info(ticker_symbol: str):
    """Get full ticker info with special handling for gold and Polygon.io first, then fallbacks"""
    cache_key = f"full_{ticker_symbol}"
    
    # Check cache first
    cached_data = get_from_cache(cache_key)
    if cached_data:
        print(f"Using cached full data for {ticker_symbol}, source: {cached_data.get('source', 'unknown')}")
        return cached_data
    
    import asyncio
    
    print(f"Fetching fresh full data for {ticker_symbol}...")
    
    # Primary: Try to get basic price data from our real APIs
    price_data = None
    
    # Special case: Handle XAU (gold) with Coinbase API
    if ticker_symbol.upper() == 'XAU':
        try:
            print(f"Attempting Coinbase gold API for full info on {ticker_symbol}")
            gold_data = asyncio.run(get_coinbase_gold_price())
            if gold_data:
                price_data = gold_data
                print(f"Coinbase gold success for full info on {ticker_symbol}: ${price_data['price']}")
        except Exception as e:
            print(f"Coinbase gold API failed for full info on {ticker_symbol}: {e}")
    
    # Try Polygon.io if not gold or if gold failed
    if not price_data:
        try:
            print(f"Attempting Polygon.io for full info on {ticker_symbol}")
            polygon_data = asyncio.run(get_polygon_real_data(ticker_symbol))
            if polygon_data:
                price_data = polygon_data
                print(f"Polygon.io success for full info on {ticker_symbol}: ${price_data['price']}")
        except Exception as e:
            print(f"Polygon.io failed for full info on {ticker_symbol}: {e}")
    
    # If we got real price data, combine with company info
    if price_data:
        try:
            # For gold, use special company info
            if ticker_symbol.upper() == 'XAU':
                gold_company_info = {
                    'longName': 'Gold Spot Price (XAU/USD)',
                    'industry': 'Precious Metals',
                    'sector': 'Commodities',
                    'marketCap': None,
                    'employees': None,
                    'city': 'Global',
                    'state': 'Global',
                    'country': 'Global',
                    'website': 'https://www.coinbase.com',
                    'commodity': 'gold',
                    'currency_pair': 'XAU/USD'
                }
                
                combined_data = {
                    **gold_company_info,
                    **price_data,    # Real price data from Coinbase
                    'currentPrice': price_data['price'],
                    'source': f"{price_data['source']}_with_gold_info"
                }
            else:
                # For stocks, use basic company info structure
                stock_company_info = {
                    'longName': f'{ticker_symbol.upper()} Stock',
                    'industry': 'Unknown',
                    'sector': 'Unknown',
                    'marketCap': None,
                    'employees': None,
                    'city': 'Unknown',
                    'state': 'Unknown',
                    'country': 'Unknown',
                    'website': None
                }
                
                # Combine real price data with basic company info
                combined_data = {
                    **stock_company_info,
                    **price_data,    # Real price data
                    'currentPrice': price_data['price'],
                    'source': f"{price_data['source']}_with_basic_info"
                }
            
            set_cache(cache_key, combined_data)
            return combined_data
            
        except Exception as e:
            print(f"Failed to combine real and company data: {e}")
    
    # No data available - return error
    print(f"ERROR: All data sources failed for full info on {ticker_symbol}")
    raise HTTPException(
        status_code=500, 
        detail=f"Unable to fetch full information for symbol '{ticker_symbol}': All data sources unavailable"
    )

@app.get("/")
def read_root():
    return {"Hello": "World testing again"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "2.0.0"
    }

@app.get("/ticket/price/{ticker}", response_class=PlainTextResponse)
def read_ticket_price(ticker: str):
    ticker_symbol = ticker_dict.get(ticker, ticker)
    data = get_ticker_price_data(ticker_symbol)
    
    # Log the data source for debugging
    source = data.get("source", "unknown")
    print(f"Returning real data for {ticker_symbol}, source: {source}")
    
    return str(data["price"])

@app.get("/ticket/{ticker}")
def read_ticket(ticker: str):
    ticker_symbol = ticker_dict.get(ticker, ticker)
    return get_ticker_full_info(ticker_symbol)

app.include_router(api_router, prefix="/api/v1")


###############################################################################
#   Run the self contained application                                        #
###############################################################################
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)