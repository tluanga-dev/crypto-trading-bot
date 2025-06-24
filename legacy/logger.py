import os
import sys
from loguru import logger
from config import Config

def setup_logger():
    """Configure and setup the application logger."""
    
    # Remove default logger
    logger.remove()
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(Config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Console logging format
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # File logging format (more detailed)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # Add console handler
    logger.add(
        sys.stdout,
        format=console_format,
        level=Config.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file handler for general logs
    logger.add(
        Config.LOG_FILE,
        format=file_format,
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # Add separate file handler for trading-specific logs
    trading_log_file = Config.LOG_FILE.replace('.log', '_trading.log')
    logger.add(
        trading_log_file,
        format=file_format,
        level="INFO",
        rotation="5 MB",
        retention="30 days",
        compression="zip",
        filter=lambda record: "trading" in record["name"].lower() or 
                              "binance" in record["name"].lower() or 
                              "portfolio" in record["name"].lower() or
                              "strategy" in record["name"].lower(),
        backtrace=True,
        diagnose=True
    )
    
    # Add error-only log file
    error_log_file = Config.LOG_FILE.replace('.log', '_errors.log')
    logger.add(
        error_log_file,
        format=file_format,
        level="ERROR",
        rotation="1 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    logger.info("Logger initialized successfully")
    logger.debug(f"Log level: {Config.LOG_LEVEL}")
    logger.debug(f"Main log file: {Config.LOG_FILE}")
    logger.debug(f"Trading log file: {trading_log_file}")
    logger.debug(f"Error log file: {error_log_file}")


def get_logger(name: str = None):
    """Get a logger instance with optional name."""
    if name:
        return logger.bind(name=name)
    return logger


class TradingLogger:
    """Specialized logger for trading operations."""
    
    def __init__(self):
        self.logger = get_logger("trading")
    
    def log_trade_signal(self, symbol: str, signal: dict):
        """Log trading signal generation."""
        self.logger.info(
            f"SIGNAL | {symbol} | Action: {signal.get('action', 'N/A')} | "
            f"Confidence: {signal.get('confidence', 0):.2f} | "
            f"Reason: {signal.get('reason', 'N/A')}"
        )
    
    def log_order_placed(self, symbol: str, side: str, quantity: float, price: float, order_id: str = None):
        """Log order placement."""
        self.logger.info(
            f"ORDER_PLACED | {symbol} | {side.upper()} | "
            f"Qty: {quantity} | Price: {price} | ID: {order_id or 'N/A'}"
        )
    
    def log_order_filled(self, symbol: str, side: str, quantity: float, price: float, pnl: float = None):
        """Log order execution."""
        pnl_str = f" | PnL: {pnl:.4f}" if pnl is not None else ""
        self.logger.info(
            f"ORDER_FILLED | {symbol} | {side.upper()} | "
            f"Qty: {quantity} | Price: {price}{pnl_str}"
        )
    
    def log_position_opened(self, symbol: str, side: str, quantity: float, entry_price: float):
        """Log position opening."""
        self.logger.info(
            f"POSITION_OPENED | {symbol} | {side.upper()} | "
            f"Qty: {quantity} | Entry: {entry_price}"
        )
    
    def log_position_closed(self, symbol: str, side: str, quantity: float, exit_price: float, pnl: float):
        """Log position closing."""
        pnl_status = "PROFIT" if pnl > 0 else "LOSS"
        self.logger.info(
            f"POSITION_CLOSED | {symbol} | {side.upper()} | "
            f"Qty: {quantity} | Exit: {exit_price} | PnL: {pnl:.4f} | {pnl_status}"
        )
    
    def log_risk_event(self, event_type: str, details: str):
        """Log risk management events."""
        self.logger.warning(f"RISK_EVENT | {event_type} | {details}")
    
    def log_balance_update(self, old_balance: float, new_balance: float, change: float):
        """Log balance changes."""
        change_pct = (change / old_balance * 100) if old_balance > 0 else 0
        self.logger.info(
            f"BALANCE_UPDATE | Old: {old_balance:.4f} | New: {new_balance:.4f} | "
            f"Change: {change:.4f} ({change_pct:+.2f}%)"
        )
    
    def log_market_data(self, symbol: str, price: float, volume: float = None, indicators: dict = None):
        """Log market data updates."""
        volume_str = f" | Vol: {volume:.2f}" if volume else ""
        indicators_str = ""
        
        if indicators:
            ind_parts = []
            for key, value in indicators.items():
                if isinstance(value, (int, float)):
                    ind_parts.append(f"{key}: {value:.2f}")
            if ind_parts:
                indicators_str = f" | {' | '.join(ind_parts)}"
        
        self.logger.debug(f"MARKET_DATA | {symbol} | Price: {price}{volume_str}{indicators_str}")
    
    def log_strategy_performance(self, strategy_name: str, metrics: dict):
        """Log strategy performance metrics."""
        self.logger.info(
            f"STRATEGY_PERFORMANCE | {strategy_name} | "
            f"Win Rate: {metrics.get('win_rate', 0)*100:.1f}% | "
            f"Total PnL: {metrics.get('total_pnl', 0):.4f} | "
            f"Trades: {metrics.get('total_trades', 0)}"
        )
    
    def log_api_error(self, operation: str, error: str, symbol: str = None):
        """Log API errors."""
        symbol_str = f" | Symbol: {symbol}" if symbol else ""
        self.logger.error(f"API_ERROR | Operation: {operation} | Error: {error}{symbol_str}")
    
    def log_system_event(self, event: str, details: str = None):
        """Log system events."""
        details_str = f" | {details}" if details else ""
        self.logger.info(f"SYSTEM_EVENT | {event}{details_str}")


class PerformanceLogger:
    """Logger for performance monitoring."""
    
    def __init__(self):
        self.logger = get_logger("performance")
    
    def log_execution_time(self, operation: str, execution_time: float):
        """Log operation execution time."""
        self.logger.debug(f"EXECUTION_TIME | {operation} | {execution_time:.4f}s")
    
    def log_memory_usage(self, operation: str, memory_mb: float):
        """Log memory usage."""
        self.logger.debug(f"MEMORY_USAGE | {operation} | {memory_mb:.2f}MB")
    
    def log_api_rate_limit(self, endpoint: str, requests_remaining: int, reset_time: int):
        """Log API rate limit status."""
        self.logger.debug(
            f"RATE_LIMIT | {endpoint} | Remaining: {requests_remaining} | "
            f"Reset: {reset_time}s"
        )


# Initialize logger when module is imported
setup_logger()

# Create global logger instances
trading_logger = TradingLogger()
performance_logger = PerformanceLogger()