"""
Multi-Symbol Monitoring and Market Scanner
Professional watchlist, market scanner, and multi-symbol data management for trading terminal.
"""

import asyncio
from typing import Dict, List, Set, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
import json

from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from loguru import logger

from websocket_manager import get_websocket_manager
from events import get_event_subscriber, get_event_publisher
from config import Config


@dataclass
class SymbolData:
    """Data container for a single symbol."""
    symbol: str
    last_price: float = 0.0
    price_change_24h: float = 0.0
    volume_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    last_update: Optional[datetime] = None
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    trade_count: int = 0
    rsi: Optional[float] = None
    macd: Optional[float] = None
    signal_action: Optional[str] = None
    signal_confidence: Optional[float] = None
    
    # Technical analysis flags
    is_oversold: bool = False
    is_overbought: bool = False
    is_trending_up: bool = False
    is_trending_down: bool = False
    is_breaking_resistance: bool = False
    is_breaking_support: bool = False
    
    # Alert flags
    has_price_alert: bool = False
    has_volume_alert: bool = False
    has_signal_alert: bool = False


@dataclass
class ScanCriteria:
    """Criteria for market scanning."""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_volume_24h: Optional[float] = None
    min_price_change: Optional[float] = None
    max_price_change: Optional[float] = None
    min_rsi: Optional[float] = None
    max_rsi: Optional[float] = None
    require_trend_up: bool = False
    require_trend_down: bool = False
    require_oversold: bool = False
    require_overbought: bool = False
    require_breakout: bool = False
    exclude_stablecoins: bool = True


class SymbolFilter:
    """Symbol filtering and categorization utilities."""
    
    MAJOR_PAIRS = {
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 
        'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LTCUSDT'
    }
    
    DEFI_TOKENS = {
        'UNIUSDT', 'AAVEUSDT', 'COMPUSDT', 'MKRUSDT', 'SUSHIUSDT',
        'CRVUSDT', '1INCHUSDT', 'YFIUSDT', 'SNXUSDT', 'BALUSDT'
    }
    
    STABLECOINS = {
        'USDCUSDT', 'BUSDUSDT', 'TUSDUSDT', 'USDPUSDT', 'DAIUSDT'
    }
    
    MEME_COINS = {
        'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT', 'BABYDOGEUSDT'
    }
    
    @classmethod
    def get_category(cls, symbol: str) -> str:
        """Get the category of a symbol."""
        if symbol in cls.MAJOR_PAIRS:
            return "major"
        elif symbol in cls.DEFI_TOKENS:
            return "defi"
        elif symbol in cls.STABLECOINS:
            return "stable"
        elif symbol in cls.MEME_COINS:
            return "meme"
        else:
            return "alt"
    
    @classmethod
    def get_popular_symbols(cls, category: str = "all") -> Set[str]:
        """Get popular symbols by category."""
        if category == "major":
            return cls.MAJOR_PAIRS.copy()
        elif category == "defi":
            return cls.DEFI_TOKENS.copy()
        elif category == "stable":
            return cls.STABLECOINS.copy()
        elif category == "meme":
            return cls.MEME_COINS.copy()
        else:
            return cls.MAJOR_PAIRS | cls.DEFI_TOKENS


class MultiSymbolMonitor:
    """
    Professional multi-symbol monitoring system.
    Manages watchlists, market scanning, and real-time data for multiple symbols.
    """
    
    def __init__(self):
        self.ws_manager = get_websocket_manager()
        self.event_subscriber = get_event_subscriber()
        self.event_publisher = get_event_publisher()
        
        # Data storage
        self.symbol_data: Dict[str, SymbolData] = {}
        self.watchlist: Set[str] = set()
        self.monitored_symbols: Set[str] = set()
        
        # Alert system
        self.price_alerts: Dict[str, List[Dict]] = defaultdict(list)
        self.volume_alerts: Dict[str, Dict] = {}
        self.signal_alerts: Set[str] = set()
        
        # Scanning and filtering
        self.scan_results: List[SymbolData] = []
        self.last_scan_time: Optional[datetime] = None
        self.scan_criteria: Optional[ScanCriteria] = None
        
        # Performance tracking
        self.update_counts: Dict[str, int] = defaultdict(int)
        self.last_performance_check = datetime.now()
        
        # Configuration
        self.max_monitored_symbols = 50
        self.scan_interval = 30  # seconds
        self.alert_cooldown = 60  # seconds
        
        # Setup event handlers
        self._setup_event_handlers()
        
        logger.info("Multi-Symbol Monitor initialized")
    
    def _setup_event_handlers(self):
        """Setup event handlers for real-time data updates."""
        
        def on_market_data(event):
            symbol = event.symbol
            if symbol in self.monitored_symbols:
                self._update_symbol_data(symbol, {
                    'price': event.price,
                    'volume': event.volume,
                    'timestamp': event.timestamp
                })
        
        def on_order_book_update(event):
            symbol = event.data.get('symbol')
            if symbol in self.monitored_symbols:
                bids = event.data.get('bids', [])
                asks = event.data.get('asks', [])
                
                if bids and asks:
                    bid_price = bids[0][0] if bids else 0
                    ask_price = asks[0][0] if asks else 0
                    spread = ask_price - bid_price if bid_price and ask_price else 0
                    
                    self._update_symbol_data(symbol, {
                        'bid': bid_price,
                        'ask': ask_price,
                        'spread': spread
                    })
        
        def on_trade_data(event):
            symbol = event.data.get('symbol')
            if symbol in self.monitored_symbols:
                data = self.symbol_data.get(symbol)
                if data:
                    data.trade_count += 1
        
        # Subscribe to events
        self.event_subscriber.on_market_data(on_market_data)
        self.event_subscriber.on_order_book_update(on_order_book_update)
        self.event_subscriber.on_trade_data(on_trade_data)
    
    def _update_symbol_data(self, symbol: str, update_data: Dict):
        """Update data for a specific symbol."""
        if symbol not in self.symbol_data:
            self.symbol_data[symbol] = SymbolData(symbol=symbol)
        
        data = self.symbol_data[symbol]
        
        # Update basic data
        if 'price' in update_data:
            data.last_price = update_data['price']
        if 'volume' in update_data and update_data['volume']:
            data.volume_24h = update_data['volume']
        if 'timestamp' in update_data:
            data.last_update = update_data['timestamp']
        if 'bid' in update_data:
            data.bid = update_data['bid']
        if 'ask' in update_data:
            data.ask = update_data['ask']
        if 'spread' in update_data:
            data.spread = update_data['spread']
        
        # Update statistics from WebSocket manager
        stats = self.ws_manager.get_symbol_statistics(symbol)
        if stats:
            data.price_change_24h = stats.get('price_change_24h', 0)
            data.high_24h = stats.get('high_24h', 0)
            data.low_24h = stats.get('low_24h', 0)
        
        # Update performance counter
        self.update_counts[symbol] += 1
        
        # Check alerts
        self._check_alerts(symbol, data)
    
    def _check_alerts(self, symbol: str, data: SymbolData):
        """Check if any alerts should be triggered for a symbol."""
        current_time = datetime.now()
        
        # Price alerts
        for alert in self.price_alerts[symbol]:
            alert_price = alert['price']
            alert_type = alert['type']  # 'above' or 'below'
            last_triggered = alert.get('last_triggered', datetime.min)
            
            if (current_time - last_triggered).seconds > self.alert_cooldown:
                if alert_type == 'above' and data.last_price >= alert_price:
                    self._trigger_price_alert(symbol, data.last_price, alert_price, 'above')
                    alert['last_triggered'] = current_time
                elif alert_type == 'below' and data.last_price <= alert_price:
                    self._trigger_price_alert(symbol, data.last_price, alert_price, 'below')
                    alert['last_triggered'] = current_time
        
        # Volume alerts
        if symbol in self.volume_alerts:
            alert = self.volume_alerts[symbol]
            threshold = alert['threshold']
            last_triggered = alert.get('last_triggered', datetime.min)
            
            if (current_time - last_triggered).seconds > self.alert_cooldown:
                if data.volume_24h > threshold:
                    self._trigger_volume_alert(symbol, data.volume_24h, threshold)
                    alert['last_triggered'] = current_time
    
    def _trigger_price_alert(self, symbol: str, current_price: float, alert_price: float, direction: str):
        """Trigger a price alert."""
        message = f"{symbol} price {direction} {alert_price:.4f} (current: {current_price:.4f})"
        self.event_publisher.publish_system_event("price_alert", message)
        logger.info(f"Price alert triggered: {message}")
    
    def _trigger_volume_alert(self, symbol: str, current_volume: float, threshold: float):
        """Trigger a volume alert."""
        message = f"{symbol} volume spike: {current_volume:,.0f} (threshold: {threshold:,.0f})"
        self.event_publisher.publish_system_event("volume_alert", message)
        logger.info(f"Volume alert triggered: {message}")
    
    async def add_symbol(self, symbol: str) -> bool:
        """Add a symbol to monitoring."""
        if len(self.monitored_symbols) >= self.max_monitored_symbols:
            logger.warning(f"Maximum monitored symbols reached ({self.max_monitored_symbols})")
            return False
        
        if symbol not in self.monitored_symbols:
            try:
                # Subscribe to WebSocket streams
                await self.ws_manager.subscribe_symbol(symbol, ['ticker', 'depth20', 'trade'])
                
                # Add to monitoring set
                self.monitored_symbols.add(symbol)
                
                # Initialize symbol data
                if symbol not in self.symbol_data:
                    self.symbol_data[symbol] = SymbolData(symbol=symbol)
                
                logger.info(f"Added {symbol} to monitoring")
                return True
                
            except Exception as e:
                logger.error(f"Failed to add {symbol} to monitoring: {e}")
                return False
        
        return True
    
    async def remove_symbol(self, symbol: str):
        """Remove a symbol from monitoring."""
        if symbol in self.monitored_symbols:
            try:
                # Unsubscribe from WebSocket streams
                await self.ws_manager.unsubscribe_symbol(symbol)
                
                # Remove from sets
                self.monitored_symbols.discard(symbol)
                self.watchlist.discard(symbol)
                
                # Clean up alerts
                if symbol in self.price_alerts:
                    del self.price_alerts[symbol]
                if symbol in self.volume_alerts:
                    del self.volume_alerts[symbol]
                self.signal_alerts.discard(symbol)
                
                logger.info(f"Removed {symbol} from monitoring")
                
            except Exception as e:
                logger.error(f"Failed to remove {symbol} from monitoring: {e}")
    
    def add_to_watchlist(self, symbol: str):
        """Add a symbol to the watchlist."""
        self.watchlist.add(symbol)
        asyncio.create_task(self.add_symbol(symbol))
    
    def remove_from_watchlist(self, symbol: str):
        """Remove a symbol from the watchlist."""
        self.watchlist.discard(symbol)
        # Keep monitoring but remove from watchlist
    
    def set_price_alert(self, symbol: str, price: float, alert_type: str = 'above'):
        """Set a price alert for a symbol."""
        alert = {
            'price': price,
            'type': alert_type,  # 'above' or 'below'
            'created': datetime.now(),
            'last_triggered': datetime.min
        }
        self.price_alerts[symbol].append(alert)
        
        if symbol not in self.monitored_symbols:
            asyncio.create_task(self.add_symbol(symbol))
        
        logger.info(f"Set price alert for {symbol}: {alert_type} {price:.4f}")
    
    def set_volume_alert(self, symbol: str, threshold: float):
        """Set a volume alert for a symbol."""
        alert = {
            'threshold': threshold,
            'created': datetime.now(),
            'last_triggered': datetime.min
        }
        self.volume_alerts[symbol] = alert
        
        if symbol not in self.monitored_symbols:
            asyncio.create_task(self.add_symbol(symbol))
        
        logger.info(f"Set volume alert for {symbol}: {threshold:,.0f}")
    
    async def scan_market(self, criteria: ScanCriteria) -> List[SymbolData]:
        """Scan the market based on criteria."""
        self.scan_criteria = criteria
        self.scan_results.clear()
        
        # Get list of symbols to scan
        if criteria.exclude_stablecoins:
            scan_symbols = SymbolFilter.get_popular_symbols("major") | SymbolFilter.get_popular_symbols("defi")
        else:
            scan_symbols = SymbolFilter.get_popular_symbols("all")
        
        # Ensure symbols are being monitored
        for symbol in scan_symbols:
            if symbol not in self.monitored_symbols:
                await self.add_symbol(symbol)
        
        # Wait a bit for data to populate
        await asyncio.sleep(2)
        
        # Apply criteria
        for symbol in scan_symbols:
            data = self.symbol_data.get(symbol)
            if not data or not data.last_price:
                continue
            
            if self._matches_criteria(data, criteria):
                self.scan_results.append(data)
        
        # Sort by criteria relevance
        self.scan_results.sort(key=lambda x: x.price_change_24h, reverse=True)
        self.last_scan_time = datetime.now()
        
        logger.info(f"Market scan completed: {len(self.scan_results)} symbols match criteria")
        return self.scan_results
    
    def _matches_criteria(self, data: SymbolData, criteria: ScanCriteria) -> bool:
        """Check if symbol data matches scan criteria."""
        # Price filters
        if criteria.min_price and data.last_price < criteria.min_price:
            return False
        if criteria.max_price and data.last_price > criteria.max_price:
            return False
        
        # Volume filter
        if criteria.min_volume_24h and data.volume_24h < criteria.min_volume_24h:
            return False
        
        # Price change filters
        if criteria.min_price_change and data.price_change_24h < criteria.min_price_change:
            return False
        if criteria.max_price_change and data.price_change_24h > criteria.max_price_change:
            return False
        
        # RSI filters
        if criteria.min_rsi and (not data.rsi or data.rsi < criteria.min_rsi):
            return False
        if criteria.max_rsi and (not data.rsi or data.rsi > criteria.max_rsi):
            return False
        
        # Technical flags
        if criteria.require_trend_up and not data.is_trending_up:
            return False
        if criteria.require_trend_down and not data.is_trending_down:
            return False
        if criteria.require_oversold and not data.is_oversold:
            return False
        if criteria.require_overbought and not data.is_overbought:
            return False
        if criteria.require_breakout and not (data.is_breaking_resistance or data.is_breaking_support):
            return False
        
        return True
    
    def get_watchlist_data(self) -> List[SymbolData]:
        """Get data for all watchlist symbols."""
        return [self.symbol_data[symbol] for symbol in self.watchlist if symbol in self.symbol_data]
    
    def get_monitored_symbols(self) -> List[str]:
        """Get list of currently monitored symbols."""
        return list(self.monitored_symbols)
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics."""
        current_time = datetime.now()
        uptime = current_time - self.last_performance_check
        
        total_updates = sum(self.update_counts.values())
        updates_per_second = total_updates / uptime.total_seconds() if uptime.total_seconds() > 0 else 0
        
        stats = {
            'monitored_symbols': len(self.monitored_symbols),
            'watchlist_size': len(self.watchlist),
            'total_updates': total_updates,
            'updates_per_second': updates_per_second,
            'uptime_seconds': uptime.total_seconds(),
            'last_scan_time': self.last_scan_time,
            'scan_results_count': len(self.scan_results),
            'active_price_alerts': sum(len(alerts) for alerts in self.price_alerts.values()),
            'active_volume_alerts': len(self.volume_alerts)
        }
        
        return stats


# Singleton instance
_multi_symbol_monitor: Optional[MultiSymbolMonitor] = None

def get_multi_symbol_monitor() -> MultiSymbolMonitor:
    """Get the singleton multi-symbol monitor."""
    global _multi_symbol_monitor
    if _multi_symbol_monitor is None:
        _multi_symbol_monitor = MultiSymbolMonitor()
    return _multi_symbol_monitor