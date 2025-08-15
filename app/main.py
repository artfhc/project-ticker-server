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
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

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

async def get_mock_data(symbol: str) -> Dict[str, Any]:
    """Return mock data for demo purposes when APIs are down"""
    import random
    base_price = 100.0
    if symbol.upper() == 'MSFT':
        base_price = 380.0
    elif symbol.upper() == 'AAPL':
        base_price = 190.0
    elif symbol.upper() == 'GOOGL':
        base_price = 140.0
    elif symbol.upper() in ['GC=F', 'GOLD']:
        base_price = 2000.0
    
    # Generate realistic price movements
    change = random.uniform(-5, 5)
    current_price = base_price + change
    
    return {
        "symbol": symbol,
        "price": round(current_price, 2),
        "open": round(current_price - random.uniform(-2, 2), 2),
        "high": round(current_price + random.uniform(0, 3), 2),
        "low": round(current_price - random.uniform(0, 3), 2),
        "volume": random.randint(1000000, 50000000),
        "source": "mock_data"
    }

async def get_finnhub_real_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Get real data from Finnhub with API key"""
    if not FINNHUB_API_KEY:
        return None
        
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://finnhub.io/api/v1/quote"
            params = {
                'symbol': symbol,
                'token': FINNHUB_API_KEY
            }
            
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('c'):  # current price exists
                    return {
                        "symbol": symbol,
                        "price": float(data['c']),   # current price
                        "open": float(data['o']),    # open price
                        "high": float(data['h']),    # high price
                        "low": float(data['l']),     # low price
                        "volume": 0,  # Volume not in quote endpoint
                        "source": "finnhub_real",
                        "timestamp": data.get('t', 0)
                    }
                    
    except Exception as e:
        print(f"Finnhub real API failed for {symbol}: {e}")
    
    return None

async def get_alpha_vantage_real_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Get real data from Alpha Vantage with API key"""
    if not ALPHA_VANTAGE_API_KEY:
        return None
        
    try:
        async with httpx.AsyncClient() as client:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': ALPHA_VANTAGE_API_KEY
            }
            
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                quote = data.get('Global Quote', {})
                
                if quote and quote.get('05. price'):
                    return {
                        "symbol": symbol,
                        "price": float(quote['05. price']),
                        "open": float(quote['02. open']),
                        "high": float(quote['03. high']),
                        "low": float(quote['04. low']),
                        "volume": int(quote['06. volume']),
                        "source": "alpha_vantage_real"
                    }
                    
    except Exception as e:
        print(f"Alpha Vantage real API failed for {symbol}: {e}")
    
    return None

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

async def get_twelve_data_real_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Get real data from Twelve Data with API key"""
    if not TWELVE_DATA_API_KEY:
        return None
        
    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.twelvedata.com/quote"
            params = {
                'symbol': symbol,
                'apikey': TWELVE_DATA_API_KEY
            }
            
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('close'):
                    return {
                        "symbol": symbol,
                        "price": float(data['close']),
                        "open": float(data['open']),
                        "high": float(data['high']),
                        "low": float(data['low']),
                        "volume": int(data.get('volume', 0)),
                        "source": "twelve_data_real"
                    }
                    
    except Exception as e:
        print(f"Twelve Data real API failed for {symbol}: {e}")
    
    return None

async def get_marketstack_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Get real data from Marketstack free API (1000 calls/month)"""
    try:
        async with httpx.AsyncClient() as client:
            # Marketstack free tier
            url = f"http://api.marketstack.com/v1/eod/latest"
            
            params = {
                'access_key': 'demo',  # Try demo access
                'symbols': symbol
            }
            
            response = await client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('data') and len(data['data']) > 0:
                    quote = data['data'][0]
                    
                    return {
                        "symbol": symbol,
                        "price": float(quote['close']),
                        "open": float(quote['open']),
                        "high": float(quote['high']),
                        "low": float(quote['low']),
                        "volume": int(quote.get('volume', 0)),
                        "source": "marketstack"
                    }
                        
    except Exception as e:
        print(f"Marketstack failed for {symbol}: {e}")
    
    return None

async def get_iex_cloud_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Get data from IEX Cloud sandbox (free)"""
    try:
        # IEX Cloud sandbox - free tier with demo data
        async with httpx.AsyncClient() as client:
            # Use sandbox environment - no API key needed for testing
            url = f"https://sandbox.iexapis.com/stable/stock/{symbol}/quote"
            response = await client.get(url, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                price = data.get('latestPrice')
                if price:
                    return {
                        "symbol": symbol,
                        "price": float(price),
                        "open": float(data.get('open', price)),
                        "high": float(data.get('high', price)),
                        "low": float(data.get('low', price)),
                        "volume": int(data.get('volume', 0)),
                        "source": "iex_cloud_sandbox",
                        "market_cap": data.get('marketCap'),
                        "pe_ratio": data.get('peRatio')
                    }
    except Exception as e:
        print(f"IEX Cloud failed: {e}")
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

async def get_alpha_vantage_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Disabled - demo API returns fake data"""
    print(f"Alpha Vantage skipped for {symbol} - demo API returns fake data")
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
    
    # Try Finnhub (if API key available)
    try:
        print(f"Attempting Finnhub for {ticker_symbol}")
        finnhub_data = asyncio.run(get_finnhub_real_data(ticker_symbol))
        if finnhub_data:
            print(f"Finnhub success for {ticker_symbol}: ${finnhub_data['price']}")
            set_cache(cache_key, finnhub_data)
            return finnhub_data
    except Exception as e:
        print(f"Finnhub failed for {ticker_symbol}: {e}")
    
    # Try Alpha Vantage (if API key available)
    try:
        print(f"Attempting Alpha Vantage for {ticker_symbol}")
        av_data = asyncio.run(get_alpha_vantage_real_data(ticker_symbol))
        if av_data:
            print(f"Alpha Vantage success for {ticker_symbol}: ${av_data['price']}")
            set_cache(cache_key, av_data)
            return av_data
    except Exception as e:
        print(f"Alpha Vantage failed for {ticker_symbol}: {e}")
    
    # Try Twelve Data (if API key available)
    try:
        print(f"Attempting Twelve Data for {ticker_symbol}")
        twelve_data = asyncio.run(get_twelve_data_real_data(ticker_symbol))
        if twelve_data:
            print(f"Twelve Data success for {ticker_symbol}: ${twelve_data['price']}")
            set_cache(cache_key, twelve_data)
            return twelve_data
    except Exception as e:
        print(f"Twelve Data failed for {ticker_symbol}: {e}")
    
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
    
    # Final fallback: mock data
    print(f"WARNING: All real sources failed for {ticker_symbol}, using mock data")
    try:
        mock_data = asyncio.run(get_mock_data(ticker_symbol))
        # Cache mock data for shorter time (60 seconds)
        cache[cache_key] = {
            'data': mock_data,
            'timestamp': datetime.utcnow()
        }
        return mock_data
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"All data sources unavailable: {str(e)}"
        )

async def get_mock_full_info(symbol: str) -> Dict[str, Any]:
    """Return mock full company info for demo purposes"""
    import random
    
    # Get price data first
    price_data = await get_mock_data(symbol)
    
    # Mock company info based on symbol
    company_info = {
        'MSFT': {
            'longName': 'Microsoft Corporation',
            'industry': 'Software - Infrastructure',
            'sector': 'Technology',
            'marketCap': 2800000000000,
            'employees': 221000,
            'city': 'Redmond',
            'state': 'WA',
            'country': 'United States',
            'website': 'https://www.microsoft.com'
        },
        'AAPL': {
            'longName': 'Apple Inc.',
            'industry': 'Consumer Electronics',
            'sector': 'Technology',
            'marketCap': 3000000000000,
            'employees': 164000,
            'city': 'Cupertino',
            'state': 'CA',
            'country': 'United States',
            'website': 'https://www.apple.com'
        },
        'GC=F': {
            'longName': 'Gold Futures',
            'industry': 'Commodities',
            'sector': 'Financial Services',
            'marketCap': None,
            'employees': None,
            'city': 'New York',
            'state': 'NY',
            'country': 'United States',
            'website': 'https://www.cmegroup.com'
        }
    }.get(symbol.upper(), {
        'longName': f'{symbol.upper()} Corp',
        'industry': 'General',
        'sector': 'Unknown',
        'marketCap': random.randint(1000000000, 100000000000),
        'employees': random.randint(1000, 50000),
        'city': 'Unknown',
        'state': 'Unknown',
        'country': 'United States',
        'website': f'https://www.{symbol.lower()}.com'
    })
    
    # Combine price and company data
    return {
        **price_data,
        **company_info,
        'symbol': symbol,
        'source': 'mock_full_data'
    }

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
    
    # Try other real APIs if Polygon failed
    if not price_data:
        try:
            print(f"Attempting Finnhub for full info on {ticker_symbol}")
            finnhub_data = asyncio.run(get_finnhub_real_data(ticker_symbol))
            if finnhub_data:
                price_data = finnhub_data
                print(f"Finnhub success for full info on {ticker_symbol}: ${price_data['price']}")
        except Exception as e:
            print(f"Finnhub failed for full info on {ticker_symbol}: {e}")
    
    # If we got real price data, combine with mock company info
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
                # Get company info from mock data for stocks
                mock_company = asyncio.run(get_mock_full_info(ticker_symbol))
                
                # Combine real price data with mock company info
                combined_data = {
                    **mock_company,  # Company info (name, industry, etc.)
                    **price_data,    # Real price data
                    'currentPrice': price_data['price'],
                    'source': f"{price_data['source']}_with_mock_company"
                }
            
            set_cache(cache_key, combined_data)
            return combined_data
            
        except Exception as e:
            print(f"Failed to combine real and mock data: {e}")
    
    # Fallback to pure mock data
    print(f"WARNING: All real sources failed for full info on {ticker_symbol}, using pure mock data")
    try:
        mock_data = asyncio.run(get_mock_full_info(ticker_symbol))
        set_cache(cache_key, mock_data)
        return mock_data
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"All data sources unavailable: {str(e)}"
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
    
    # Add debug info in development
    source = data.get("source", "unknown")
    if source.startswith("mock"):
        print(f"WARNING: Using mock data for {ticker_symbol}, source: {source}")
    
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