"""
Binance API service for fetching market data
"""
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
import httpx
from app.core.config import settings
from app.models.market import MarketData, KlineData, OrderBook, OrderBookEntry
from app.models.symbol import Symbol, SymbolInfo
import logging

logger = logging.getLogger(__name__)


class BinanceService:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3" if not settings.BINANCE_TESTNET else "https://testnet.binance.vision/api/v3"
        self.ws_base_url = "wss://stream.binance.com:9443/ws" if not settings.BINANCE_TESTNET else "wss://testnet.binance.vision/ws"
        self.client = httpx.AsyncClient(timeout=30.0)
        self._symbols_cache: Optional[List[Symbol]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = 3600  # 1 hour cache
    
    async def close(self):
        await self.client.aclose()
    
    async def get_all_symbols(self) -> List[Symbol]:
        """Get all trading symbols from Binance"""
        # Check cache
        if self._symbols_cache and self._cache_timestamp:
            cache_age = (datetime.utcnow() - self._cache_timestamp).total_seconds()
            if cache_age < self._cache_duration:
                return self._symbols_cache
        
        try:
            response = await self.client.get(f"{self.base_url}/exchangeInfo")
            response.raise_for_status()
            data = response.json()
            
            symbols = []
            for symbol_data in data["symbols"]:
                if symbol_data["status"] == "TRADING":
                    symbol = Symbol(
                        symbol=symbol_data["symbol"],
                        base_asset=symbol_data["baseAsset"],
                        quote_asset=symbol_data["quoteAsset"],
                        status=symbol_data["status"],
                        is_spot_trading_allowed=symbol_data.get("isSpotTradingAllowed", False),
                        is_margin_trading_allowed=symbol_data.get("isMarginTradingAllowed", False),
                        filters=symbol_data.get("filters", {})
                    )
                    symbols.append(symbol)
            
            # Update cache
            self._symbols_cache = symbols
            self._cache_timestamp = datetime.utcnow()
            
            return symbols
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            raise
    
    async def search_symbols(self, query: str) -> List[Symbol]:
        """Search symbols by query"""
        all_symbols = await self.get_all_symbols()
        query_upper = query.upper()
        
        filtered_symbols = [
            symbol for symbol in all_symbols
            if query_upper in symbol.symbol or 
               query_upper in symbol.base_asset or 
               query_upper in symbol.quote_asset
        ]
        
        return filtered_symbols[:50]  # Limit to 50 results
    
    async def get_market_data(self, symbol: str) -> MarketData:
        """Get current market data for a symbol"""
        try:
            # Get 24hr ticker data
            ticker_response = await self.client.get(
                f"{self.base_url}/ticker/24hr",
                params={"symbol": symbol}
            )
            ticker_response.raise_for_status()
            ticker = ticker_response.json()
            
            # Get current best bid/ask
            book_ticker_response = await self.client.get(
                f"{self.base_url}/ticker/bookTicker",
                params={"symbol": symbol}
            )
            book_ticker_response.raise_for_status()
            book_ticker = book_ticker_response.json()
            
            return MarketData(
                symbol=symbol,
                current_price=float(ticker["lastPrice"]),
                timestamp=datetime.utcnow(),
                volume_24h=float(ticker["volume"]),
                high_24h=float(ticker["highPrice"]),
                low_24h=float(ticker["lowPrice"]),
                price_change_24h=float(ticker["priceChange"]),
                price_change_percent_24h=float(ticker["priceChangePercent"]),
                bid_price=float(book_ticker["bidPrice"]),
                ask_price=float(book_ticker["askPrice"]),
                last_trade_price=float(ticker["lastPrice"])
            )
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            raise
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> List[KlineData]:
        """Get kline/candlestick data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                }
            )
            response.raise_for_status()
            data = response.json()
            
            klines = []
            for kline in data:
                klines.append(KlineData(
                    open_time=kline[0],
                    open=float(kline[1]),
                    high=float(kline[2]),
                    low=float(kline[3]),
                    close=float(kline[4]),
                    volume=float(kline[5]),
                    close_time=kline[6],
                    quote_volume=float(kline[7]),
                    trades=kline[8],
                    taker_buy_base_volume=float(kline[9]),
                    taker_buy_quote_volume=float(kline[10])
                ))
            
            return klines
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            raise
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> OrderBook:
        """Get order book depth"""
        try:
            response = await self.client.get(
                f"{self.base_url}/depth",
                params={
                    "symbol": symbol,
                    "limit": limit
                }
            )
            response.raise_for_status()
            data = response.json()
            
            bids = [OrderBookEntry(price=float(bid[0]), quantity=float(bid[1])) for bid in data["bids"]]
            asks = [OrderBookEntry(price=float(ask[0]), quantity=float(ask[1])) for ask in data["asks"]]
            
            return OrderBook(
                symbol=symbol,
                bids=bids,
                asks=asks,
                last_update_id=data["lastUpdateId"],
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            raise
    
    async def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades"""
        try:
            response = await self.client.get(
                f"{self.base_url}/trades",
                params={
                    "symbol": symbol,
                    "limit": limit
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching recent trades for {symbol}: {e}")
            raise


# Singleton instance
_binance_service: Optional[BinanceService] = None


async def get_binance_service() -> BinanceService:
    global _binance_service
    if _binance_service is None:
        _binance_service = BinanceService()
    return _binance_service