"""
Demo Binance Client for testing without API keys.
Provides simulated market data and trading functionality.
"""

import time
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from config import Config


class DemoBinanceClient:
    """Demo Binance client that simulates API responses without requiring credentials."""
    
    def __init__(self):
        """Initialize demo client."""
        self.base_prices = {
            'BTCUSDT': 70000.0,
            'ETHUSDT': 3500.0,
            'BNBUSDT': 600.0,
            'ADAUSDT': 0.5,
            'XRPUSDT': 0.6,
            'SOLUSDT': 100.0,
            'DOGEUSDT': 0.08,
            'LTCUSDT': 100.0,
            'DOTUSDT': 7.0,
            'AVAXUSDT': 35.0
        }
        self.start_time = datetime.now()
        logger.info("Demo Binance client initialized (No API keys required)")
    
    def test_connection(self) -> bool:
        """Simulate connection test."""
        logger.info("Demo: Connected to simulated Binance API")
        return True
    
    def get_account_info(self) -> Dict[str, Any]:
        """Simulate account information."""
        return {
            'accountType': 'DEMO',
            'balances': [
                {'asset': 'USDT', 'free': '50000.00', 'locked': '0.00'},
                {'asset': 'BTC', 'free': '0.00', 'locked': '0.00'},
                {'asset': 'ETH', 'free': '0.00', 'locked': '0.00'}
            ],
            'canTrade': True,
            'canWithdraw': False,
            'canDeposit': False,
            'updateTime': int(time.time() * 1000)
        }
    
    def get_symbol_ticker(self, symbol: str) -> Dict[str, Any]:
        """Simulate ticker information."""
        base_price = self.base_prices.get(symbol, 100.0)
        
        # Add some random variation
        price_variation = random.uniform(-0.02, 0.02)  # ±2%
        current_price = base_price * (1 + price_variation)
        
        return {
            'symbol': symbol,
            'price': f"{current_price:.8f}"
        }
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Simulate historical kline data."""
        base_price = self.base_prices.get(symbol, 100.0)
        klines = []
        
        # Calculate interval in minutes
        interval_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440
        }.get(interval, 1)
        
        # Generate historical data
        for i in range(limit):
            timestamp = int((datetime.now() - timedelta(minutes=(limit - i) * interval_minutes)).timestamp() * 1000)
            
            # Simulate price movement
            price_change = random.uniform(-0.01, 0.01)  # ±1% per candle
            price = base_price * (1 + price_change * (i / limit))
            
            # OHLCV data
            open_price = price * random.uniform(0.998, 1.002)
            close_price = price * random.uniform(0.998, 1.002)
            high_price = max(open_price, close_price) * random.uniform(1.001, 1.005)
            low_price = min(open_price, close_price) * random.uniform(0.995, 0.999)
            volume = random.uniform(100, 10000)
            
            kline = [
                timestamp,  # Open time
                f"{open_price:.8f}",  # Open
                f"{high_price:.8f}",  # High
                f"{low_price:.8f}",   # Low
                f"{close_price:.8f}", # Close
                f"{volume:.8f}",      # Volume
                timestamp + (interval_minutes * 60000) - 1,  # Close time
                f"{volume * close_price:.8f}",  # Quote asset volume
                random.randint(10, 1000),  # Number of trades
                f"{volume * 0.6:.8f}",     # Taker buy base volume
                f"{volume * close_price * 0.6:.8f}",  # Taker buy quote volume
                "0"  # Ignore
            ]
            klines.append(kline)
        
        return klines
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Simulate order book data."""
        base_price = self.base_prices.get(symbol, 100.0)
        
        # Generate bid/ask levels
        bids = []
        asks = []
        
        # Generate realistic order book
        for i in range(min(limit, 20)):
            # Bids (buy orders) - below current price
            bid_price = base_price * (1 - (i + 1) * 0.0001)
            bid_quantity = random.uniform(0.1, 10.0)
            bids.append([f"{bid_price:.8f}", f"{bid_quantity:.8f}"])
            
            # Asks (sell orders) - above current price
            ask_price = base_price * (1 + (i + 1) * 0.0001)
            ask_quantity = random.uniform(0.1, 10.0)
            asks.append([f"{ask_price:.8f}", f"{ask_quantity:.8f}"])
        
        return {
            'lastUpdateId': int(time.time() * 1000),
            'bids': bids,
            'asks': asks
        }
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Simulate recent trades."""
        base_price = self.base_prices.get(symbol, 100.0)
        trades = []
        
        for i in range(min(limit, 50)):
            timestamp = int((datetime.now() - timedelta(seconds=i * 10)).timestamp() * 1000)
            price = base_price * random.uniform(0.999, 1.001)
            quantity = random.uniform(0.01, 5.0)
            
            trade = {
                'id': int(time.time() * 1000) + i,
                'price': f"{price:.8f}",
                'qty': f"{quantity:.8f}",
                'time': timestamp,
                'isBuyerMaker': random.choice([True, False])
            }
            trades.append(trade)
        
        return trades
    
    def place_order(self, symbol: str, side: str, order_type: str, 
                   quantity: float, price: Optional[float] = None) -> Dict[str, Any]:
        """Simulate order placement."""
        order_id = f"DEMO_{int(time.time() * 1000)}"
        
        # Simulate successful order
        return {
            'symbol': symbol,
            'orderId': order_id,
            'clientOrderId': f"demo_{order_id}",
            'transactTime': int(time.time() * 1000),
            'price': f"{price:.8f}" if price else "0.00000000",
            'origQty': f"{quantity:.8f}",
            'executedQty': f"{quantity:.8f}",  # Assume immediate fill in demo
            'status': 'FILLED',
            'type': order_type,
            'side': side
        }
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Simulate order cancellation."""
        return {
            'symbol': symbol,
            'orderId': order_id,
            'status': 'CANCELED',
            'clientOrderId': f"demo_{order_id}"
        }
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Simulate open orders (empty for demo)."""
        return []
    
    def get_all_orders(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Simulate order history (empty for demo)."""
        return []


class BinanceClientFactory:
    """Factory to create appropriate Binance client based on configuration."""
    
    @staticmethod
    def create_client():
        """Create appropriate client based on trading mode."""
        if Config.is_demo_mode():
            return DemoBinanceClient()
        else:
            # Import the real client only when needed
            from binance_client import BinanceClient
            return BinanceClient()