"""
Binance WebSocket manager for real-time data streaming
"""
import asyncio
import json
import logging
from typing import Dict, Set, Optional, Callable, Any
from datetime import datetime
import websockets
from websockets.exceptions import WebSocketException
from app.core.config import settings
from app.models.market import PriceUpdate, KlineUpdate, OrderBookUpdate, TradeUpdate, KlineData

logger = logging.getLogger(__name__)


class BinanceWebSocketManager:
    def __init__(self):
        self.base_url = "wss://stream.binance.com:9443/ws" if not settings.BINANCE_TESTNET else "wss://testnet.binance.vision/ws"
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # symbol -> set of stream types
        self.callbacks: Dict[str, Callable] = {}
        self.is_running = False
        self.reconnect_delay = settings.WS_RECONNECT_INTERVAL
        self.tasks: Dict[str, asyncio.Task] = {}
        
    async def start(self):
        """Start the WebSocket manager"""
        self.is_running = True
        logger.info("Binance WebSocket manager started")
        
    async def stop(self):
        """Stop all WebSocket connections"""
        self.is_running = False
        
        # Cancel all tasks
        for task in self.tasks.values():
            task.cancel()
            
        # Close all connections
        for stream_id, ws in self.connections.items():
            try:
                await ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket {stream_id}: {e}")
                
        self.connections.clear()
        self.tasks.clear()
        logger.info("Binance WebSocket manager stopped")
    
    def set_callback(self, event_type: str, callback: Callable):
        """Set callback for specific event type"""
        self.callbacks[event_type] = callback
        
    async def subscribe_ticker(self, symbol: str):
        """Subscribe to ticker stream for a symbol"""
        stream_name = f"{symbol.lower()}@ticker"
        await self._subscribe_stream(stream_name, symbol, "ticker")
        
    async def subscribe_klines(self, symbol: str, interval: str):
        """Subscribe to kline stream for a symbol and interval"""
        stream_name = f"{symbol.lower()}@kline_{interval}"
        await self._subscribe_stream(stream_name, symbol, f"kline_{interval}")
        
    async def subscribe_depth(self, symbol: str):
        """Subscribe to order book depth stream"""
        stream_name = f"{symbol.lower()}@depth20@100ms"
        await self._subscribe_stream(stream_name, symbol, "depth")
        
    async def subscribe_trades(self, symbol: str):
        """Subscribe to trade stream"""
        stream_name = f"{symbol.lower()}@trade"
        await self._subscribe_stream(stream_name, symbol, "trade")
        
    async def unsubscribe(self, symbol: str, stream_type: Optional[str] = None):
        """Unsubscribe from streams for a symbol"""
        symbol_lower = symbol.lower()
        
        if stream_type:
            # Unsubscribe from specific stream type
            streams_to_remove = []
            for stream_id in self.connections:
                if symbol_lower in stream_id and stream_type in stream_id:
                    streams_to_remove.append(stream_id)
                    
            for stream_id in streams_to_remove:
                await self._close_stream(stream_id)
                if symbol in self.subscriptions and stream_type in self.subscriptions[symbol]:
                    self.subscriptions[symbol].remove(stream_type)
        else:
            # Unsubscribe from all streams for this symbol
            streams_to_remove = [s for s in self.connections if symbol_lower in s]
            for stream_id in streams_to_remove:
                await self._close_stream(stream_id)
            if symbol in self.subscriptions:
                del self.subscriptions[symbol]
                
    async def _subscribe_stream(self, stream_name: str, symbol: str, stream_type: str):
        """Subscribe to a specific stream"""
        if stream_name in self.connections:
            logger.debug(f"Already subscribed to {stream_name}")
            return
            
        # Track subscription
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = set()
        self.subscriptions[symbol].add(stream_type)
        
        # Create connection task
        task = asyncio.create_task(self._maintain_connection(stream_name))
        self.tasks[stream_name] = task
        logger.info(f"Subscribed to {stream_name}")
        
    async def _close_stream(self, stream_id: str):
        """Close a specific stream"""
        if stream_id in self.tasks:
            self.tasks[stream_id].cancel()
            del self.tasks[stream_id]
            
        if stream_id in self.connections:
            try:
                await self.connections[stream_id].close()
            except Exception as e:
                logger.error(f"Error closing stream {stream_id}: {e}")
            del self.connections[stream_id]
            
    async def _maintain_connection(self, stream_name: str):
        """Maintain WebSocket connection with auto-reconnect"""
        reconnect_count = 0
        max_reconnects = 10
        
        while self.is_running and reconnect_count < max_reconnects:
            try:
                url = f"{self.base_url}/{stream_name}"
                logger.info(f"Connecting to {url}")
                
                async with websockets.connect(url) as websocket:
                    self.connections[stream_name] = websocket
                    reconnect_count = 0  # Reset on successful connection
                    
                    # Listen for messages
                    async for message in websocket:
                        if not self.is_running:
                            break
                            
                        try:
                            data = json.loads(message)
                            await self._handle_message(stream_name, data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse message from {stream_name}: {e}")
                        except Exception as e:
                            logger.error(f"Error handling message from {stream_name}: {e}")
                            
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Connection closed for {stream_name}")
            except Exception as e:
                logger.error(f"WebSocket error for {stream_name}: {e}")
                
            # Remove from connections
            if stream_name in self.connections:
                del self.connections[stream_name]
                
            # Reconnect logic
            if self.is_running and reconnect_count < max_reconnects:
                reconnect_count += 1
                delay = self.reconnect_delay * reconnect_count
                logger.info(f"Reconnecting to {stream_name} in {delay}s (attempt {reconnect_count})")
                await asyncio.sleep(delay)
                
        logger.warning(f"Max reconnection attempts reached for {stream_name}")
        
    async def _handle_message(self, stream_name: str, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        try:
            if "@ticker" in stream_name:
                await self._handle_ticker_update(data)
            elif "@kline" in stream_name:
                await self._handle_kline_update(data)
            elif "@depth" in stream_name:
                await self._handle_depth_update(data)
            elif "@trade" in stream_name:
                await self._handle_trade_update(data)
        except Exception as e:
            logger.error(f"Error processing message from {stream_name}: {e}")
            
    async def _handle_ticker_update(self, data: Dict[str, Any]):
        """Handle ticker update"""
        update = PriceUpdate(
            symbol=data["s"],
            price=float(data["c"]),
            volume=float(data["v"]),
            timestamp=datetime.utcnow()
        )
        
        if "price_update" in self.callbacks:
            await self.callbacks["price_update"](update)
            
    async def _handle_kline_update(self, data: Dict[str, Any]):
        """Handle kline update"""
        kline_data = data["k"]
        update = KlineUpdate(
            symbol=kline_data["s"],
            interval=kline_data["i"],
            kline=KlineData(
                open_time=kline_data["t"],
                open=float(kline_data["o"]),
                high=float(kline_data["h"]),
                low=float(kline_data["l"]),
                close=float(kline_data["c"]),
                volume=float(kline_data["v"]),
                close_time=kline_data["T"],
                quote_volume=float(kline_data["q"]),
                trades=kline_data["n"],
                taker_buy_base_volume=float(kline_data["V"]),
                taker_buy_quote_volume=float(kline_data["Q"])
            ),
            timestamp=datetime.utcnow()
        )
        
        if "kline_update" in self.callbacks:
            await self.callbacks["kline_update"](update)
            
    async def _handle_depth_update(self, data: Dict[str, Any]):
        """Handle order book depth update"""
        update = OrderBookUpdate(
            symbol=data["s"],
            bids=[[float(bid[0]), float(bid[1])] for bid in data["b"]],
            asks=[[float(ask[0]), float(ask[1])] for ask in data["a"]],
            timestamp=datetime.utcnow()
        )
        
        if "orderbook_update" in self.callbacks:
            await self.callbacks["orderbook_update"](update)
            
    async def _handle_trade_update(self, data: Dict[str, Any]):
        """Handle trade update"""
        update = TradeUpdate(
            symbol=data["s"],
            price=float(data["p"]),
            quantity=float(data["q"]),
            is_buyer_maker=data["m"],
            timestamp=datetime.utcnow()
        )
        
        if "trade_update" in self.callbacks:
            await self.callbacks["trade_update"](update)
            
    def get_active_subscriptions(self) -> Dict[str, Set[str]]:
        """Get active subscriptions"""
        return self.subscriptions.copy()
        
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all streams"""
        return {
            stream_id: stream_id in self.connections and self.connections[stream_id].open
            for stream_id in self.tasks.keys()
        }


# Singleton instance
_ws_manager: Optional[BinanceWebSocketManager] = None


async def get_ws_manager() -> BinanceWebSocketManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = BinanceWebSocketManager()
        await _ws_manager.start()
    return _ws_manager