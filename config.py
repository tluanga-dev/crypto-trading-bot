import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Centralized configuration management for the trading application."""
    
    # Binance API Configuration
    BINANCE_API_KEY: str = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY: str = os.getenv('BINANCE_SECRET_KEY', '')
    
    # Trading Configuration
    TRADING_MODE: str = os.getenv('TRADING_MODE', 'testnet')
    DEFAULT_SYMBOL: str = os.getenv('DEFAULT_SYMBOL', 'BTCUSDT')
    DEFAULT_QUANTITY: float = float(os.getenv('DEFAULT_QUANTITY', '0.001'))
    
    # Risk Management
    MAX_POSITION_SIZE: float = float(os.getenv('MAX_POSITION_SIZE', '0.1'))
    STOP_LOSS_PERCENTAGE: float = float(os.getenv('STOP_LOSS_PERCENTAGE', '2.0'))
    TAKE_PROFIT_PERCENTAGE: float = float(os.getenv('TAKE_PROFIT_PERCENTAGE', '5.0'))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/trading.log')
    
    # Analysis Configuration
    ANALYSIS_TIMEFRAME: str = os.getenv('ANALYSIS_TIMEFRAME', '1h')
    ANALYSIS_LOOKBACK_PERIODS: int = int(os.getenv('ANALYSIS_LOOKBACK_PERIODS', '100'))
    
    # Database Configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///trading_data.db')
    
    # Notification Configuration
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')
    
    @classmethod
    def validate_required_config(cls) -> bool:
        """Validate that required configuration values are present."""
        required_fields = ['BINANCE_API_KEY', 'BINANCE_SECRET_KEY']
        
        for field in required_fields:
            if not getattr(cls, field):
                raise ValueError(f"Required configuration field '{field}' is missing or empty")
        
        return True
    
    @classmethod
    def is_testnet_mode(cls) -> bool:
        """Check if application is running in testnet mode."""
        return cls.TRADING_MODE.lower() == 'testnet'
    
    @classmethod
    def get_binance_base_url(cls) -> str:
        """Get the appropriate Binance API base URL based on trading mode."""
        if cls.is_testnet_mode():
            return "https://testnet.binance.vision"
        return "https://api.binance.com"
    
    @classmethod
    def print_config_summary(cls):
        """Print a summary of current configuration (excluding sensitive data)."""
        print("=== Trading Bot Configuration ===")
        print(f"Trading Mode: {cls.TRADING_MODE}")
        print(f"Default Symbol: {cls.DEFAULT_SYMBOL}")
        print(f"Default Quantity: {cls.DEFAULT_QUANTITY}")
        print(f"Max Position Size: {cls.MAX_POSITION_SIZE * 100}%")
        print(f"Stop Loss: {cls.STOP_LOSS_PERCENTAGE}%")
        print(f"Take Profit: {cls.TAKE_PROFIT_PERCENTAGE}%")
        print(f"Analysis Timeframe: {cls.ANALYSIS_TIMEFRAME}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("================================")