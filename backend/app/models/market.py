"""
Market data models
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class Timeframe(str, Enum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


class PriceData(BaseModel):
    symbol: str
    price: float
    timestamp: datetime
    volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_percent_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None


class KlineData(BaseModel):
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    quote_volume: float
    trades: int
    taker_buy_base_volume: float
    taker_buy_quote_volume: float


class OrderBookEntry(BaseModel):
    price: float
    quantity: float


class OrderBook(BaseModel):
    symbol: str
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
    last_update_id: int
    timestamp: datetime


class TradeData(BaseModel):
    id: int
    price: float
    quantity: float
    timestamp: datetime
    is_buyer_maker: bool


class MarketData(BaseModel):
    symbol: str
    current_price: float
    timestamp: datetime
    volume_24h: float
    high_24h: float
    low_24h: float
    price_change_24h: float
    price_change_percent_24h: float
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    last_trade_price: Optional[float] = None


class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PriceUpdate(BaseModel):
    type: str = "price_update"
    symbol: str
    price: float
    volume: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class KlineUpdate(BaseModel):
    type: str = "kline_update"
    symbol: str
    interval: str
    kline: KlineData
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OrderBookUpdate(BaseModel):
    type: str = "orderbook_update"
    symbol: str
    bids: List[List[float]]  # [[price, quantity], ...]
    asks: List[List[float]]  # [[price, quantity], ...]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TradeUpdate(BaseModel):
    type: str = "trade_update"
    symbol: str
    price: float
    quantity: float
    is_buyer_maker: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)