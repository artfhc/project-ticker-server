from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TickerPriceResponse(BaseModel):
    """Response model for ticker price endpoint"""
    symbol: str = Field(..., description="The ticker symbol")
    price: float = Field(..., description="Current price")
    open: Optional[float] = Field(None, description="Opening price")
    high: Optional[float] = Field(None, description="Highest price")
    low: Optional[float] = Field(None, description="Lowest price")
    volume: Optional[int] = Field(None, description="Trading volume")
    source: str = Field(..., description="Data source")
    timestamp: Optional[int] = Field(None, description="Data timestamp")
    currency: Optional[str] = Field("USD", description="Price currency")


class TickerInfoResponse(BaseModel):
    """Response model for full ticker information"""
    symbol: str = Field(..., description="The ticker symbol")
    price: float = Field(..., description="Current price")
    current_price: float = Field(..., alias="currentPrice", description="Current price (alias)")
    open: Optional[float] = Field(None, description="Opening price")
    high: Optional[float] = Field(None, description="Highest price")
    low: Optional[float] = Field(None, description="Lowest price")
    volume: Optional[int] = Field(None, description="Trading volume")
    
    # Company information
    long_name: Optional[str] = Field(None, alias="longName", description="Company full name")
    industry: Optional[str] = Field(None, description="Industry sector")
    sector: Optional[str] = Field(None, description="Business sector")
    market_cap: Optional[int] = Field(None, alias="marketCap", description="Market capitalization")
    employees: Optional[int] = Field(None, description="Number of employees")
    city: Optional[str] = Field(None, description="Company city")
    state: Optional[str] = Field(None, description="Company state")
    country: Optional[str] = Field(None, description="Company country")
    website: Optional[str] = Field(None, description="Company website")
    
    # Metadata
    source: str = Field(..., description="Data source")
    timestamp: Optional[int] = Field(None, description="Data timestamp")
    currency: Optional[str] = Field("USD", description="Price currency")
    commodity: Optional[str] = Field(None, description="Commodity type if applicable")
    currency_pair: Optional[str] = Field(None, alias="currencyPair", description="Currency pair if applicable")

    class Config:
        allow_population_by_field_name = True


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Service version")


class CacheClearResponse(BaseModel):
    """Response model for cache clear operation"""
    message: str = Field(..., description="Operation result message")
    cleared: bool = Field(..., description="Whether cache was successfully cleared")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Operation timestamp")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")