"""
Shared Pydantic models for the cryptocurrency trading application.
Used by both CLI and API interfaces.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum

class TradingMode(str, Enum):
    """Trading mode enumeration."""
    TESTNET = "testnet"
    LIVE = "live"

class SignalAction(str, Enum):
    """Trading signal actions."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class PositionSide(str, Enum):
    """Position side enumeration."""
    BUY = "buy"
    SELL = "sell"

class PositionStatus(str, Enum):
    """Position status enumeration."""
    OPEN = "open"
    CLOSED = "closed"

# Market Data Models
class MarketSummary(BaseModel):
    """Market summary data."""
    current_price: float
    price_change_24h: float
    volume_24h: float
    rsi: float
    macd: float
    bb_position: float
    signal: int
    signal_strength: float
    support_level: float
    resistance_level: float

class TrendAnalysis(BaseModel):
    """Market trend analysis."""
    trend: Literal["bullish", "bearish", "sideways"]
    strength: Literal["weak", "moderate", "strong"]
    price_slope: float
    volatility: float

class TradingSignal(BaseModel):
    """Trading signal model."""
    action: SignalAction
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class MarketAnalysis(BaseModel):
    """Complete market analysis."""
    symbol: str
    market_summary: MarketSummary
    trend_analysis: TrendAnalysis
    strategy_signal: TradingSignal
    timestamp: datetime

# Portfolio Models
class PositionData(BaseModel):
    """Position data model."""
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    pnl: float
    status: PositionStatus

class PerformanceMetrics(BaseModel):
    """Portfolio performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float = Field(ge=0.0, le=1.0)
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    total_return: float

class RiskMetrics(BaseModel):
    """Risk management metrics."""
    daily_loss: float
    max_daily_loss: float
    max_position_size: float
    max_drawdown_limit: float

class PortfolioSummary(BaseModel):
    """Portfolio summary data."""
    initial_balance: float
    current_balance: float
    unrealized_pnl: float
    portfolio_value: float
    open_positions: int
    open_positions_details: List[PositionData]
    performance_metrics: PerformanceMetrics
    risk_metrics: RiskMetrics

# Trading Request Models
class PositionRequest(BaseModel):
    """Request to open a new position."""
    symbol: str = Field(min_length=1)
    strategy: Optional[str] = "rsi_macd"
    quantity: Optional[float] = Field(gt=0, default=None)

class StrategyRequest(BaseModel):
    """Request to change strategy."""
    strategy_name: str = Field(min_length=1)

# Response Models
class AnalysisResponse(BaseModel):
    """Market analysis API response."""
    symbol: str
    current_price: float
    price_change_24h: float
    rsi: float
    macd: float
    signal: TradingSignal
    trend: TrendAnalysis
    timestamp: datetime

class PortfolioResponse(BaseModel):
    """Portfolio API response."""
    initial_balance: float
    current_balance: float
    unrealized_pnl: float
    portfolio_value: float
    open_positions: int
    performance_metrics: PerformanceMetrics

class PositionResponse(BaseModel):
    """Position API response."""
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    pnl: float
    status: PositionStatus

class StrategiesResponse(BaseModel):
    """Available strategies response."""
    strategies: List[str]
    active_strategy: str

class TradeExecutionResult(BaseModel):
    """Result of trade execution."""
    status: Literal["success", "blocked", "exists", "no_signal", "error"]
    message: str
    position: Optional[PositionData] = None
    reason: Optional[str] = None

class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "unhealthy"]
    timestamp: datetime
    version: str
    trading_mode: TradingMode
    uptime_seconds: Optional[float] = None

# WebSocket Message Models
class WebSocketMessage(BaseModel):
    """Base WebSocket message."""
    type: str
    timestamp: datetime

class MarketUpdateMessage(WebSocketMessage):
    """Market data update via WebSocket."""
    type: Literal["market_update"] = "market_update"
    symbol: str
    data: MarketSummary

class SignalUpdateMessage(WebSocketMessage):
    """Trading signal update via WebSocket."""
    type: Literal["signal_update"] = "signal_update"
    symbol: str
    signal: TradingSignal

class PortfolioUpdateMessage(WebSocketMessage):
    """Portfolio update via WebSocket."""
    type: Literal["portfolio_update"] = "portfolio_update"
    data: PortfolioSummary

class PositionUpdateMessage(WebSocketMessage):
    """Position update via WebSocket."""
    type: Literal["position_update"] = "position_update"
    action: Literal["opened", "closed", "modified"]
    position: PositionData

class WebSocketSubscribeMessage(BaseModel):
    """WebSocket subscription message from client."""
    type: Literal["subscribe"]
    symbol: Optional[str] = None
    subscriptions: Optional[List[str]] = None

# Configuration Models
class TradingConfig(BaseModel):
    """Trading configuration model."""
    trading_mode: TradingMode
    default_symbol: str
    default_quantity: float
    max_position_size: float
    stop_loss_percentage: float
    take_profit_percentage: float
    analysis_timeframe: str
    analysis_lookback_periods: int

# Error Models
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
    request_id: Optional[str] = None

# Event Models (for internal event system)
class TradingEvent(BaseModel):
    """Base trading event."""
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]

class MarketDataEvent(TradingEvent):
    """Market data update event."""
    event_type: Literal["market_data"] = "market_data"
    symbol: str
    price: float
    volume: Optional[float] = None

class SignalGeneratedEvent(TradingEvent):
    """Trading signal generated event."""
    event_type: Literal["signal_generated"] = "signal_generated"
    symbol: str
    signal: TradingSignal

class PositionOpenedEvent(TradingEvent):
    """Position opened event."""
    event_type: Literal["position_opened"] = "position_opened"
    position: PositionData

class PositionClosedEvent(TradingEvent):
    """Position closed event."""
    event_type: Literal["position_closed"] = "position_closed"
    position: PositionData

class RiskEvent(TradingEvent):
    """Risk management event."""
    event_type: Literal["risk_event"] = "risk_event"
    risk_type: str
    message: str
    severity: Literal["info", "warning", "critical"]

class SystemEvent(TradingEvent):
    """System event."""
    event_type: Literal["system_event"] = "system_event"
    system_action: str
    message: str