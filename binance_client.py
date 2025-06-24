import time
from typing import Dict, List, Optional, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from loguru import logger
from config import Config

class BinanceClient:
    """Enhanced Binance API client with error handling and rate limiting."""
    
    def __init__(self):
        """Initialize Binance client with configuration."""
        try:
            Config.validate_required_config()
            
            self.client = Client(
                api_key=Config.BINANCE_API_KEY,
                api_secret=Config.BINANCE_SECRET_KEY,
                testnet=Config.is_testnet_mode()
            )
            
            # Test connection
            self.test_connection()
            
            logger.info(f"Binance client initialized successfully (Mode: {Config.TRADING_MODE})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to Binance API."""
        try:
            self.client.ping()
            server_time = self.client.get_server_time()
            logger.info(f"Connected to Binance API. Server time: {server_time}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        try:
            account_info = self.client.get_account()
            logger.debug("Retrieved account information")
            return account_info
        except BinanceAPIException as e:
            logger.error(f"Failed to get account info: {e}")
            raise
    
    def get_symbol_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker information for a symbol."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            logger.debug(f"Retrieved ticker for {symbol}: {ticker['price']}")
            return ticker
        except BinanceAPIException as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            raise
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Get historical kline/candlestick data."""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            logger.debug(f"Retrieved {len(klines)} klines for {symbol} ({interval})")
            return klines
        except BinanceAPIException as e:
            logger.error(f"Failed to get klines for {symbol}: {e}")
            raise
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Get order book for a symbol."""
        try:
            order_book = self.client.get_order_book(symbol=symbol, limit=limit)
            logger.debug(f"Retrieved order book for {symbol}")
            return order_book
        except BinanceAPIException as e:
            logger.error(f"Failed to get order book for {symbol}: {e}")
            raise
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades for a symbol."""
        try:
            trades = self.client.get_recent_trades(symbol=symbol, limit=limit)
            logger.debug(f"Retrieved {len(trades)} recent trades for {symbol}")
            return trades
        except BinanceAPIException as e:
            logger.error(f"Failed to get recent trades for {symbol}: {e}")
            raise
    
    def place_order(self, symbol: str, side: str, order_type: str, 
                   quantity: float, price: Optional[float] = None) -> Dict[str, Any]:
        """Place a trading order."""
        try:
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity
            }
            
            if price and order_type in ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT']:
                order_params['price'] = price
                order_params['timeInForce'] = 'GTC'
            
            # Safety check for testnet mode
            if not Config.is_testnet_mode():
                logger.warning("LIVE TRADING MODE - Order will be placed on live exchange!")
                response = input("Continue with live order? (yes/no): ")
                if response.lower() != 'yes':
                    raise Exception("Live trading order cancelled by user")
            
            order = self.client.create_order(**order_params)
            logger.info(f"Order placed successfully: {order['orderId']}")
            return order
            
        except BinanceOrderException as e:
            logger.error(f"Order failed: {e}")
            raise
        except BinanceAPIException as e:
            logger.error(f"API error while placing order: {e}")
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Cancel an existing order."""
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"Order {order_id} cancelled successfully")
            return result
        except BinanceAPIException as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders or open orders for a specific symbol."""
        try:
            orders = self.client.get_open_orders(symbol=symbol)
            logger.debug(f"Retrieved {len(orders)} open orders")
            return orders
        except BinanceAPIException as e:
            logger.error(f"Failed to get open orders: {e}")
            raise
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """Get status of a specific order."""
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            logger.debug(f"Retrieved order status for {order_id}: {order['status']}")
            return order
        except BinanceAPIException as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            raise
    
    def get_balance(self, asset: str) -> Dict[str, str]:
        """Get balance for a specific asset."""
        try:
            account = self.get_account_info()
            for balance in account['balances']:
                if balance['asset'] == asset:
                    logger.debug(f"Balance for {asset}: {balance['free']} free, {balance['locked']} locked")
                    return balance
            
            logger.warning(f"Asset {asset} not found in account balances")
            return {'asset': asset, 'free': '0.00000000', 'locked': '0.00000000'}
            
        except Exception as e:
            logger.error(f"Failed to get balance for {asset}: {e}")
            raise
    
    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get exchange information."""
        try:
            if symbol:
                info = self.client.get_symbol_info(symbol)
                logger.debug(f"Retrieved exchange info for {symbol}")
            else:
                info = self.client.get_exchange_info()
                logger.debug("Retrieved general exchange info")
            return info
        except BinanceAPIException as e:
            logger.error(f"Failed to get exchange info: {e}")
            raise