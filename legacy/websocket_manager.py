"""
WebSocket Stream Manager for Real-Time Market Data
Handles persistent WebSocket connections for tick-by-tick price feeds, order book data, and trade streams.
"""

import asyncio
import json
import time
from collections import deque, defaultdict
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime, timedelta
import websockets
from loguru import logger

from events import get_event_publisher
from config import Config


class CircularBuffer:
    """Efficient circular buffer for real-time data storage."""
    
    def __init__(self, maxsize: int = 1000):
        self.buffer = deque(maxlen=maxsize)
        self.maxsize = maxsize
    
    def append(self, item):
        self.buffer.append(item)
    
    def get_recent(self, count: int) -> List:
        """Get the most recent N items."""
        return list(self.buffer)[-count:] if count <= len(self.buffer) else list(self.buffer)
    
    def get_all(self) -> List:
        """Get all items in buffer."""
        return list(self.buffer)
    
    def clear(self):
        """Clear the buffer."""
        self.buffer.clear()
    
    def __len__(self):
        return len(self.buffer)


class MarketDataBuffer:
    """Manages multiple data streams with different buffer sizes."""
    
    def __init__(self):
        # Different buffer sizes for different data types
        self.tick_data = defaultdict(lambda: CircularBuffer(1000))  # Last 1000 ticks
        self.kline_data = defaultdict(lambda: defaultdict(lambda: CircularBuffer(500)))  # 500 candles per timeframe
        self.order_book = defaultdict(lambda: CircularBuffer(100))  # Last 100 order book snapshots
        self.trade_data = defaultdict(lambda: CircularBuffer(500))  # Last 500 individual trades
        self.volume_data = defaultdict(lambda: CircularBuffer(1000))  # Volume data
        
        # Statistics tracking
        self.symbol_stats = defaultdict(lambda: {
            'last_price': 0.0,
            'price_change_24h': 0.0,
            'volume_24h': 0.0,
            'high_24h': 0.0,
            'low_24h': 0.0,
            'last_update': None,
            'tick_count': 0,
            'trade_count': 0
        })
    
    def add_tick(self, symbol: str, data: Dict):
        """Add tick data for a symbol."""
        tick_data = {
            'symbol': symbol,
            'price': float(data.get('c', 0)),  # Current price
            'timestamp': datetime.now(),
            'volume': float(data.get('v', 0)),
            'count': int(data.get('n', 0))  # Trade count
        }
        
        self.tick_data[symbol].append(tick_data)
        
        # Update statistics
        stats = self.symbol_stats[symbol]
        stats['last_price'] = tick_data['price']
        stats['last_update'] = tick_data['timestamp']
        stats['tick_count'] += 1
        
        if 'P' in data:  # Price change percentage
            stats['price_change_24h'] = float(data['P'])
        if 'h' in data:  # High price
            stats['high_24h'] = float(data['h'])
        if 'l' in data:  # Low price
            stats['low_24h'] = float(data['l'])
        if 'v' in data:  # Volume
            stats['volume_24h'] = float(data['v'])
    
    def add_kline(self, symbol: str, interval: str, data: Dict):
        """Add kline/candlestick data."""
        kline_data = {
            'symbol': symbol,
            'interval': interval,
            'open_time': int(data['t']),
            'close_time': int(data['T']),
            'open': float(data['o']),
            'high': float(data['h']),
            'low': float(data['l']),
            'close': float(data['c']),
            'volume': float(data['v']),
            'quote_volume': float(data['q']),
            'trades': int(data['n']),
            'is_closed': data['x']  # Whether this kline is closed
        }
        
        self.kline_data[symbol][interval].append(kline_data)
    
    def add_order_book(self, symbol: str, data: Dict):
        """Add order book depth data."""
        book_data = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'bids': [(float(bid[0]), float(bid[1])) for bid in data.get('b', [])],
            'asks': [(float(ask[0]), float(ask[1])) for ask in data.get('a', [])],
            'last_update_id': data.get('u', 0)
        }
        
        self.order_book[symbol].append(book_data)
    
    def add_trade(self, symbol: str, data: Dict):
        """Add individual trade data."""
        trade_data = {
            'symbol': symbol,
            'trade_id': data.get('t'),
            'price': float(data.get('p', 0)),
            'quantity': float(data.get('q', 0)),
            'timestamp': datetime.fromtimestamp(int(data.get('T', 0)) / 1000),
            'is_buyer_maker': data.get('m', False)
        }
        
        self.trade_data[symbol].append(trade_data)
        
        # Update trade count
        self.symbol_stats[symbol]['trade_count'] += 1
    
    def get_latest_tick(self, symbol: str) -> Optional[Dict]:
        """Get the latest tick for a symbol."""
        ticks = self.tick_data[symbol].get_recent(1)
        return ticks[0] if ticks else None
    
    def get_latest_klines(self, symbol: str, interval: str, count: int = 50) -> List[Dict]:
        """Get recent klines for a symbol and interval."""
        return self.kline_data[symbol][interval].get_recent(count)
    
    def get_latest_order_book(self, symbol: str) -> Optional[Dict]:
        """Get the latest order book for a symbol."""
        books = self.order_book[symbol].get_recent(1)
        return books[0] if books else None
    
    def get_recent_trades(self, symbol: str, count: int = 50) -> List[Dict]:
        """Get recent trades for a symbol."""
        return self.trade_data[symbol].get_recent(count)
    
    def get_symbol_stats(self, symbol: str) -> Dict:
        """Get current statistics for a symbol."""
        return self.symbol_stats[symbol].copy()


class WebSocketStreamManager:
    """
    Professional WebSocket stream manager for real-time market data.
    Handles multiple concurrent streams with automatic reconnection.
    """
    
    def __init__(self):
        self.base_url = "wss://stream.binance.com:9443/ws/"
        self.testnet_url = "wss://testnet.binance.vision/ws/"
        
        # Use appropriate URL based on trading mode
        if Config.is_demo_mode():
            self.ws_url = self.testnet_url  # Use testnet URL for demo
        elif Config.is_testnet_mode():
            self.ws_url = self.testnet_url
        else:
            self.ws_url = self.base_url
        
        self.data_buffer = MarketDataBuffer()
        self.event_publisher = get_event_publisher()
        
        # Connection management
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscribed_symbols: Set[str] = set()
        self.stream_handlers: Dict[str, Callable] = {}
        self.is_running = False
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 10
        
        # Stream configurations
        self.default_streams = ['ticker', 'kline_1m', 'depth20', 'trade']
        self.kline_intervals = ['1m', '5m', '15m', '1h', '4h', '1d']
        
        # Setup stream handlers
        self._setup_stream_handlers()
        
        logger.info(f"WebSocket Stream Manager initialized with URL: {self.ws_url}")
    
    def _setup_stream_handlers(self):
        """Setup handlers for different stream types."""
        self.stream_handlers = {
            'ticker': self._handle_ticker_stream,
            'kline': self._handle_kline_stream,
            'depth': self._handle_depth_stream,
            'trade': self._handle_trade_stream,
            'miniTicker': self._handle_mini_ticker_stream
        }
    
    async def start(self):
        """Start the WebSocket stream manager."""
        self.is_running = True
        logger.info("WebSocket Stream Manager started")
    
    async def stop(self):
        """Stop all WebSocket connections."""
        self.is_running = False
        
        # Close all connections
        for stream_name, connection in self.connections.items():
            if connection and not connection.closed:
                await connection.close()
                logger.info(f"Closed WebSocket connection: {stream_name}")
        
        self.connections.clear()
        logger.info("WebSocket Stream Manager stopped")
    
    async def subscribe_symbol(self, symbol: str, streams: Optional[List[str]] = None):
        """Subscribe to real-time data for a symbol."""
        if not self.is_running:
            await self.start()
        
        if streams is None:
            streams = self.default_streams
        
        symbol_lower = symbol.lower()
        self.subscribed_symbols.add(symbol_lower)
        
        # Subscribe to each stream type
        for stream_type in streams:
            await self._subscribe_to_stream(symbol_lower, stream_type)
        
        logger.info(f"Subscribed to {symbol} with streams: {streams}")
    
    async def unsubscribe_symbol(self, symbol: str):
        """Unsubscribe from a symbol."""
        symbol_lower = symbol.lower()
        if symbol_lower in self.subscribed_symbols:
            self.subscribed_symbols.remove(symbol_lower)
            
            # Close connections for this symbol
            streams_to_close = [s for s in self.connections.keys() if symbol_lower in s]
            for stream_name in streams_to_close:
                if stream_name in self.connections:
                    await self.connections[stream_name].close()
                    del self.connections[stream_name]
            
            logger.info(f"Unsubscribed from {symbol}")
    
    async def _subscribe_to_stream(self, symbol: str, stream_type: str):
        """Subscribe to a specific stream for a symbol."""
        if stream_type == 'ticker':
            stream_name = f"{symbol}@ticker"
        elif stream_type == 'kline_1m':
            stream_name = f"{symbol}@kline_1m"
        elif stream_type == 'depth20':
            stream_name = f"{symbol}@depth20@1000ms"
        elif stream_type == 'trade':
            stream_name = f"{symbol}@trade"
        else:
            logger.warning(f"Unknown stream type: {stream_type}")
            return
        
        # Create WebSocket connection task
        task = asyncio.create_task(self._maintain_connection(stream_name))
        logger.info(f"Created connection task for stream: {stream_name}")
    
    async def _maintain_connection(self, stream_name: str):
        """Maintain a WebSocket connection with automatic reconnection."""
        reconnect_count = 0
        
        while self.is_running and reconnect_count < self.max_reconnect_attempts:
            try:
                url = f"{self.ws_url}{stream_name}"
                logger.info(f"Connecting to WebSocket: {url}")
                
                async with websockets.connect(url) as websocket:
                    self.connections[stream_name] = websocket
                    reconnect_count = 0  # Reset on successful connection
                    
                    logger.info(f"Connected to stream: {stream_name}")
                    
                    # Listen for messages
                    async for message in websocket:
                        if not self.is_running:
                            break
                        
                        try:
                            data = json.loads(message)
                            await self._handle_message(stream_name, data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse message: {e}")
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
            
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"WebSocket connection closed: {stream_name}")
            except Exception as e:
                logger.error(f"WebSocket connection error for {stream_name}: {e}")
            
            # Remove from connections if disconnected
            if stream_name in self.connections:
                del self.connections[stream_name]
            
            # Reconnect logic
            if self.is_running and reconnect_count < self.max_reconnect_attempts:
                reconnect_count += 1
                logger.info(f"Reconnecting to {stream_name} in {self.reconnect_delay}s (attempt {reconnect_count})")
                await asyncio.sleep(self.reconnect_delay)
        
        logger.warning(f"Max reconnection attempts reached for {stream_name}")
    
    async def _handle_message(self, stream_name: str, data: Dict):
        """Handle incoming WebSocket messages."""
        try:
            stream_type = data.get('e')  # Event type
            symbol = data.get('s', '').upper()
            
            if stream_type in self.stream_handlers:
                await self.stream_handlers[stream_type](symbol, data)
            else:
                # Handle based on stream name patterns
                if '@ticker' in stream_name:
                    await self._handle_ticker_stream(symbol, data)
                elif '@kline' in stream_name:
                    await self._handle_kline_stream(symbol, data)
                elif '@depth' in stream_name:
                    await self._handle_depth_stream(symbol, data)
                elif '@trade' in stream_name:
                    await self._handle_trade_stream(symbol, data)
        
        except Exception as e:
            logger.error(f"Error handling message from {stream_name}: {e}")
    
    async def _handle_ticker_stream(self, symbol: str, data: Dict):
        """Handle 24hr ticker statistics."""
        self.data_buffer.add_tick(symbol, data)
        
        # Publish market data event
        self.event_publisher.publish_market_data(
            symbol=symbol,
            price=float(data.get('c', 0)),
            volume=float(data.get('v', 0)),
            timestamp=datetime.now()
        )
    
    async def _handle_kline_stream(self, symbol: str, data: Dict):
        """Handle kline/candlestick data."""
        kline_data = data.get('k', {})
        interval = kline_data.get('i', '1m')
        
        self.data_buffer.add_kline(symbol, interval, kline_data)
        
        # Publish kline event for completed candles
        if kline_data.get('x', False):  # Kline is closed
            self.event_publisher.publish_kline_data(
                symbol=symbol,
                interval=interval,
                open_price=float(kline_data.get('o', 0)),
                high_price=float(kline_data.get('h', 0)),
                low_price=float(kline_data.get('l', 0)),
                close_price=float(kline_data.get('c', 0)),
                volume=float(kline_data.get('v', 0)),
                timestamp=datetime.fromtimestamp(int(kline_data.get('t', 0)) / 1000)
            )
    
    async def _handle_depth_stream(self, symbol: str, data: Dict):
        """Handle order book depth data."""
        self.data_buffer.add_order_book(symbol, data)
        
        # Publish order book event
        self.event_publisher.publish_order_book_update(
            symbol=symbol,
            bids=[(float(bid[0]), float(bid[1])) for bid in data.get('b', [])],
            asks=[(float(ask[0]), float(ask[1])) for ask in data.get('a', [])],
            timestamp=datetime.now()
        )
    
    async def _handle_trade_stream(self, symbol: str, data: Dict):
        """Handle individual trade data."""
        self.data_buffer.add_trade(symbol, data)
        
        # Publish trade event
        self.event_publisher.publish_trade_data(
            symbol=symbol,
            price=float(data.get('p', 0)),
            quantity=float(data.get('q', 0)),
            is_buyer_maker=data.get('m', False),
            timestamp=datetime.fromtimestamp(int(data.get('T', 0)) / 1000)
        )
    
    async def _handle_mini_ticker_stream(self, symbol: str, data: Dict):
        """Handle mini ticker data."""
        # Similar to ticker but with less data
        await self._handle_ticker_stream(symbol, data)
    
    # Data access methods
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest price for a symbol."""
        tick = self.data_buffer.get_latest_tick(symbol)
        return tick['price'] if tick else None
    
    def get_latest_klines(self, symbol: str, interval: str = '1m', count: int = 50) -> List[Dict]:
        """Get recent klines for charting."""
        return self.data_buffer.get_latest_klines(symbol, interval, count)
    
    def get_order_book(self, symbol: str) -> Optional[Dict]:
        """Get the latest order book."""
        return self.data_buffer.get_latest_order_book(symbol)
    
    def get_recent_trades(self, symbol: str, count: int = 50) -> List[Dict]:
        """Get recent trades."""
        return self.data_buffer.get_recent_trades(symbol, count)
    
    def get_symbol_statistics(self, symbol: str) -> Dict:
        """Get comprehensive statistics for a symbol."""
        return self.data_buffer.get_symbol_stats(symbol)
    
    def get_subscribed_symbols(self) -> List[str]:
        """Get list of currently subscribed symbols."""
        return list(self.subscribed_symbols)
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all streams."""
        status = {}
        for stream_name, connection in self.connections.items():
            status[stream_name] = connection is not None and not connection.closed
        return status


# Singleton instance
_websocket_manager: Optional[WebSocketStreamManager] = None

def get_websocket_manager() -> WebSocketStreamManager:
    """Get the singleton WebSocket stream manager."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketStreamManager()
    return _websocket_manager