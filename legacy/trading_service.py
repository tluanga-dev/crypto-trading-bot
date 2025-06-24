"""
Core Trading Service - The heart of the cryptocurrency trading application.
Contains all business logic for market analysis, trading decisions, and portfolio management.
Used by both CLI and API interfaces.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

# Import our core modules
from config import Config
from demo_client import BinanceClientFactory
from data_analyzer import DataAnalyzer
from strategy import StrategyManager
from portfolio import Portfolio, Position
from logger import trading_logger

# Import new models and events
from models import (
    MarketAnalysis, MarketSummary, TradingSignal, TrendAnalysis,
    PortfolioSummary, PositionData, TradeExecutionResult,
    TradingConfig, SignalAction, PositionSide, PositionStatus
)
from events import get_event_publisher, EventPublisher

class TradingService:
    """
    Core trading service that handles all business logic.
    This is the single source of truth for trading operations.
    """
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.binance_client = None
        self.data_analyzer = DataAnalyzer()
        self.strategy_manager = StrategyManager()
        self.portfolio = Portfolio(initial_balance)
        self.event_publisher: EventPublisher = get_event_publisher()
        
        # State tracking
        self.is_initialized = False
        self.is_monitoring = False
        self.last_analysis: Dict[str, MarketAnalysis] = {}
        self.start_time = datetime.now()
        
        # Configuration
        self.config = TradingConfig(
            trading_mode=Config.TRADING_MODE,
            default_symbol=Config.DEFAULT_SYMBOL,
            default_quantity=Config.DEFAULT_QUANTITY,
            max_position_size=Config.MAX_POSITION_SIZE,
            stop_loss_percentage=Config.STOP_LOSS_PERCENTAGE,
            take_profit_percentage=Config.TAKE_PROFIT_PERCENTAGE,
            analysis_timeframe=Config.ANALYSIS_TIMEFRAME,
            analysis_lookback_periods=Config.ANALYSIS_LOOKBACK_PERIODS
        )
        
        logger.info(f"Trading service created with balance: {initial_balance}")
    
    async def initialize(self) -> bool:
        """Initialize the trading service."""
        try:
            logger.info("Initializing trading service...")
            
            # Validate configuration
            Config.validate_required_config()
            
            # Initialize Binance client
            self.binance_client = BinanceClientFactory.create_client()
            
            # Test connection
            account_info = self.binance_client.get_account_info()
            logger.info(f"Connected to Binance account: {account_info.get('accountType', 'Unknown')}")
            
            # Publish system event
            self.event_publisher.publish_system_event(
                "service_initialized",
                f"Trading service initialized with balance: {self.initial_balance}"
            )
            
            self.is_initialized = True
            trading_logger.log_system_event("TRADING_SERVICE_INITIALIZED", f"Balance: {self.initial_balance}")
            
            logger.info("Trading service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize trading service: {e}")
            self.event_publisher.publish_system_event(
                "initialization_failed",
                f"Failed to initialize: {str(e)}"
            )
            return False
    
    async def analyze_market(self, symbol: str) -> MarketAnalysis:
        """Analyze market data for a given symbol."""
        if not self.is_initialized:
            raise RuntimeError("Trading service not initialized")
        
        try:
            logger.debug(f"Analyzing market for {symbol}")
            
            # Get market data
            klines = self.binance_client.get_klines(
                symbol=symbol,
                interval=self.config.analysis_timeframe,
                limit=self.config.analysis_lookback_periods
            )
            
            # Convert to DataFrame and add indicators
            df = self.data_analyzer.klines_to_dataframe(klines)
            df = self.data_analyzer.add_technical_indicators(df)
            df = self.data_analyzer.calculate_signals(df)
            
            # Get market summary
            market_summary_data = self.data_analyzer.get_market_summary(df)
            market_summary = MarketSummary(**market_summary_data)
            
            # Get trend analysis
            trend_data = self.data_analyzer.analyze_trend(df)
            trend_analysis = TrendAnalysis(**trend_data)
            
            # Get strategy signal
            signal_data = self.strategy_manager.get_signal(df)
            strategy_signal = TradingSignal(
                action=SignalAction(signal_data['action']),
                confidence=signal_data['confidence'],
                reason=signal_data['reason'],
                entry_price=signal_data.get('entry_price'),
                stop_loss=signal_data.get('stop_loss'),
                take_profit=signal_data.get('take_profit')
            )
            
            # Create analysis object
            analysis = MarketAnalysis(
                symbol=symbol,
                market_summary=market_summary,
                trend_analysis=trend_analysis,
                strategy_signal=strategy_signal,
                timestamp=datetime.now()
            )
            
            # Store analysis
            self.last_analysis[symbol] = analysis
            
            # Publish events
            self.event_publisher.publish_market_data(
                symbol=symbol,
                price=market_summary.current_price,
                volume=market_summary.volume_24h
            )
            
            self.event_publisher.publish_signal_generated(symbol, strategy_signal)
            
            # Log market data
            trading_logger.log_market_data(
                symbol=symbol,
                price=market_summary.current_price,
                volume=market_summary.volume_24h,
                indicators={
                    'RSI': market_summary.rsi,
                    'MACD': market_summary.macd
                }
            )
            
            logger.debug(f"Market analysis completed for {symbol}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market for {symbol}: {e}")
            raise
    
    async def execute_position(self, symbol: str, strategy: Optional[str] = None) -> TradeExecutionResult:
        """Execute a trading position based on strategy signal."""
        if not self.is_initialized:
            raise RuntimeError("Trading service not initialized")
        
        try:
            # Set strategy if provided
            if strategy:
                self.strategy_manager.set_active_strategy(strategy)
            
            # Get latest analysis
            analysis = await self.analyze_market(symbol)
            signal = analysis.strategy_signal
            
            if signal.action == SignalAction.HOLD:
                return TradeExecutionResult(
                    status="no_signal",
                    message="No trading signal generated",
                    reason=signal.reason
                )
            
            # Log the signal
            trading_logger.log_trade_signal(symbol, signal.dict())
            
            # Calculate position size
            position_size = self.portfolio.calculate_position_size(signal.confidence)
            
            # Check risk management
            can_trade, reason = self.portfolio.can_open_position(position_size)
            if not can_trade:
                self.event_publisher.publish_risk_event("trade_blocked", reason, "warning")
                trading_logger.log_risk_event("TRADE_BLOCKED", reason)
                return TradeExecutionResult(
                    status="blocked",
                    message=reason,
                    reason="risk_management"
                )
            
            # Check for existing position
            existing_position = self.portfolio.get_position_by_symbol(symbol)
            if existing_position:
                return TradeExecutionResult(
                    status="exists",
                    message=f"Position already exists for {symbol}",
                    position=self._position_to_data(existing_position)
                )
            
            # Execute trade (simulated for testnet)
            position = Position(
                symbol=symbol,
                side=signal.action.value,
                quantity=position_size / signal.entry_price,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            
            self.portfolio.add_position(position)
            
            # Convert to PositionData model
            position_data = self._position_to_data(position)
            
            # Log and publish events
            trading_logger.log_position_opened(
                symbol, signal.action.value, position.quantity, signal.entry_price
            )
            
            self.event_publisher.publish_position_opened(position_data)
            
            logger.info(f"Position opened: {symbol} {signal.action.value} {position.quantity}")
            
            return TradeExecutionResult(
                status="success",
                message=f"Position opened for {symbol}",
                position=position_data
            )
            
        except Exception as e:
            logger.error(f"Error executing position for {symbol}: {e}")
            return TradeExecutionResult(
                status="error",
                message=f"Position execution failed: {str(e)}",
                reason="execution_error"
            )
    
    async def close_position(self, symbol: str) -> TradeExecutionResult:
        """Close an existing position."""
        if not self.is_initialized:
            raise RuntimeError("Trading service not initialized")
        
        try:
            # Get current price
            ticker = self.binance_client.get_symbol_ticker(symbol)
            current_price = float(ticker['price'])
            
            # Close position
            closed_position = self.portfolio.close_position(symbol, current_price)
            
            if not closed_position:
                return TradeExecutionResult(
                    status="not_found",
                    message=f"No open position found for {symbol}"
                )
            
            # Convert to PositionData model
            position_data = self._position_to_data(closed_position)
            
            # Log and publish events
            trading_logger.log_position_closed(
                symbol, closed_position.side, closed_position.quantity,
                current_price, closed_position.pnl
            )
            
            self.event_publisher.publish_position_closed(position_data)
            
            logger.info(f"Position closed: {symbol} PnL: {closed_position.pnl:.4f}")
            
            return TradeExecutionResult(
                status="success",
                message=f"Position closed for {symbol}",
                position=position_data
            )
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return TradeExecutionResult(
                status="error",
                message=f"Position closing failed: {str(e)}",
                reason="execution_error"
            )
    
    async def monitor_positions(self):
        """Monitor open positions and execute exit conditions."""
        if not self.is_initialized:
            return
        
        try:
            open_positions = self.portfolio.get_open_positions()
            
            for position in open_positions:
                # Get current price
                ticker = self.binance_client.get_symbol_ticker(position.symbol)
                current_price = float(ticker['price'])
                
                # Update PnL
                old_pnl = position.pnl
                position.update_pnl(current_price)
                
                # Publish market data update if PnL changed significantly
                if abs(position.pnl - old_pnl) > 0.01:  # Threshold for updates
                    self.event_publisher.publish_market_data(
                        position.symbol, current_price
                    )
                
                # Check exit conditions
                should_exit = False
                exit_reason = ""
                
                # Stop loss/take profit check
                if position.side == 'buy':
                    if position.stop_loss and current_price <= position.stop_loss:
                        should_exit = True
                        exit_reason = "stop_loss_triggered"
                    elif position.take_profit and current_price >= position.take_profit:
                        should_exit = True
                        exit_reason = "take_profit_triggered"
                else:  # sell position
                    if position.stop_loss and current_price >= position.stop_loss:
                        should_exit = True
                        exit_reason = "stop_loss_triggered"
                    elif position.take_profit and current_price <= position.take_profit:
                        should_exit = True
                        exit_reason = "take_profit_triggered"
                
                if should_exit:
                    logger.info(f"Auto-closing position {position.symbol}: {exit_reason}")
                    await self.close_position(position.symbol)
                    
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    def get_portfolio_summary(self) -> PortfolioSummary:
        """Get current portfolio summary."""
        summary = self.portfolio.get_portfolio_summary()
        
        # Convert positions to PositionData models
        position_details = [
            self._position_to_data(pos) for pos in self.portfolio.get_open_positions()
        ]
        
        return PortfolioSummary(
            initial_balance=summary['initial_balance'],
            current_balance=summary['current_balance'],
            unrealized_pnl=summary['unrealized_pnl'],
            portfolio_value=summary['portfolio_value'],
            open_positions=summary['open_positions'],
            open_positions_details=position_details,
            performance_metrics=summary['performance_metrics'],
            risk_metrics=summary['risk_metrics']
        )
    
    def get_open_positions(self) -> List[PositionData]:
        """Get all open positions as PositionData models."""
        return [
            self._position_to_data(pos) 
            for pos in self.portfolio.get_open_positions()
        ]
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available trading strategies."""
        return self.strategy_manager.get_available_strategies()
    
    def set_active_strategy(self, strategy_name: str):
        """Set the active trading strategy."""
        self.strategy_manager.set_active_strategy(strategy_name)
        self.event_publisher.publish_system_event(
            "strategy_changed",
            f"Active strategy set to: {strategy_name}"
        )
    
    def get_active_strategy(self) -> str:
        """Get the currently active strategy."""
        return self.strategy_manager.active_strategy
    
    def get_last_analysis(self, symbol: str) -> Optional[MarketAnalysis]:
        """Get the last analysis for a symbol."""
        return self.last_analysis.get(symbol)
    
    def get_uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_config(self) -> TradingConfig:
        """Get trading configuration."""
        return self.config
    
    def _position_to_data(self, position: Position) -> PositionData:
        """Convert Position object to PositionData model."""
        return PositionData(
            symbol=position.symbol,
            side=PositionSide(position.side),
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=position.exit_price,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            entry_time=position.entry_time,
            exit_time=position.exit_time,
            pnl=position.pnl,
            status=PositionStatus(position.status)
        )
    
    async def start_monitoring(self, interval_seconds: int = 30):
        """Start background monitoring of positions."""
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.is_monitoring = True
        logger.info(f"Starting position monitoring (interval: {interval_seconds}s)")
        
        self.event_publisher.publish_system_event(
            "monitoring_started",
            f"Position monitoring started with {interval_seconds}s interval"
        )
        
        while self.is_monitoring:
            try:
                await self.monitor_positions()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self.is_monitoring = False
        logger.info("Position monitoring stopped")
        
        self.event_publisher.publish_system_event(
            "monitoring_stopped",
            "Position monitoring stopped"
        )
    
    async def shutdown(self):
        """Shutdown the trading service gracefully."""
        logger.info("Shutting down trading service...")
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Export final trade history
        if self.portfolio.trade_history:
            filename = self.portfolio.export_trade_history()
            logger.info(f"Trade history exported to: {filename}")
        
        # Publish shutdown event
        self.event_publisher.publish_system_event(
            "service_shutdown",
            "Trading service shutdown completed"
        )
        
        logger.info("Trading service shutdown completed")

# Factory function for creating trading service instances
def create_trading_service(initial_balance: float = 10000.0) -> TradingService:
    """Create a new trading service instance."""
    return TradingService(initial_balance)