from fastapi import FastAPI
from mangum import Mangum
import yfinance as yf

from app.api.v1.api import router as api_router

###############################################################################
#   Application object                                                        #
###############################################################################
app = FastAPI()

###############################################################################
#   Routers configuration                                                     #
###############################################################################

ticker_dict = {
    'gold': 'GC=F'
}

@app.get("/")
def read_root():
    return {"Hello": "World testing again"}

@app.get("/price/{ticker}")
def read_root(ticker: str):
    ticker_info = yf.Ticker(ticker_dict[ticker] if ticker in ticker_dict else ticker)
    return {
        "symbol": ticker_info.info['symbol'],
        "price": ticker_info.info['previousClose'],
        "volume": ticker_info.info['volume']
    }

app.include_router(api_router, prefix="/api/v1")

###############################################################################
#   Handler for AWS Lambda                                                    #
###############################################################################
handler = Mangum(app)

###############################################################################
#   Run the self contained application                                        #
###############################################################################
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)