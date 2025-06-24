#!/usr/bin/env python3
"""
FastAPI REST API Server for Cryptocurrency Trading Bot
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Import our modules
from config import Config
from binance_client import BinanceClient
from data_analyzer import DataAnalyzer
from strategy import StrategyManager
from portfolio import Portfolio, Position
from logger import trading_logger, get_logger

# Initialize logger
logger = get_logger("api_server")

# Global instances
trading_bot = None
scheduler = None
websocket_manager = None

# Pydantic models for API
class AnalysisResponse(BaseModel):
    symbol: str
    current_price: float
    price_change_24h: float
    rsi: float
    macd: float
    signal: Dict[str, Any]
    trend: Dict[str, str]
    timestamp: datetime

class PortfolioResponse(BaseModel):
    initial_balance: float
    current_balance: float
    unrealized_pnl: float
    portfolio_value: float
    open_positions: int
    performance_metrics: Dict[str, Any]

class PositionRequest(BaseModel):
    symbol: str
    strategy: Optional[str] = "rsi_macd"
    quantity: Optional[float] = None

class PositionResponse(BaseModel):
    symbol: str
    side: str
    quantity: float
    entry_price: float
    pnl: float
    status: str

class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.market_data = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict):
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_market_update(self, symbol: str, data: Dict):
        message = {
            "type": "market_update",
            "symbol": symbol,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
    
    async def send_signal_update(self, symbol: str, signal: Dict):
        message = {
            "type": "signal_update",
            "symbol": symbol,
            "signal": signal,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
    
    async def send_portfolio_update(self, portfolio_data: Dict):
        message = {
            "type": "portfolio_update",
            "data": portfolio_data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)

class TradingBotAPI:
    """Main trading bot API class."""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.binance_client = None
        self.data_analyzer = DataAnalyzer()
        self.strategy_manager = StrategyManager()
        self.portfolio = Portfolio(initial_balance)
        self.last_analysis = {}
        self.is_monitoring = False
        
    async def initialize(self):
        """Initialize the trading bot."""
        try:
            logger.info("Initializing trading bot API...")
            self.binance_client = BinanceClient()
            Config.print_config_summary()
            trading_logger.log_system_event("API_BOT_INITIALIZED", f"Balance: {self.initial_balance}")
            logger.info("Trading bot API initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize trading bot API: {e}")
            return False
    
    async def analyze_market(self, symbol: str) -> Dict:
        """Analyze market for a given symbol."""
        try:
            # Get market data
            klines = self.binance_client.get_klines(
                symbol=symbol,
                interval=Config.ANALYSIS_TIMEFRAME,
                limit=Config.ANALYSIS_LOOKBACK_PERIODS
            )
            
            # Convert to DataFrame and add indicators
            df = self.data_analyzer.klines_to_dataframe(klines)
            df = self.data_analyzer.add_technical_indicators(df)
            df = self.data_analyzer.calculate_signals(df)
            
            # Get market summary and analysis
            market_summary = self.data_analyzer.get_market_summary(df)
            trend_analysis = self.data_analyzer.analyze_trend(df)
            strategy_signal = self.strategy_manager.get_signal(df)
            
            # Store last analysis
            analysis = {
                'symbol': symbol,
                'market_summary': market_summary,
                'trend_analysis': trend_analysis,
                'strategy_signal': strategy_signal,
                'timestamp': datetime.now()
            }
            
            self.last_analysis[symbol] = analysis
            
            # Broadcast to WebSocket clients
            if websocket_manager:
                await websocket_manager.send_market_update(symbol, market_summary)
                await websocket_manager.send_signal_update(symbol, strategy_signal)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market for {symbol}: {e}")
            raise HTTPException(status_code=500, detail=f"Market analysis failed: {str(e)}")
    
    async def execute_position(self, symbol: str, strategy: str = "rsi_macd") -> Dict:
        """Execute a trading position based on strategy signal."""
        try:
            # Set strategy
            self.strategy_manager.set_active_strategy(strategy)
            
            # Get latest analysis
            analysis = await self.analyze_market(symbol)
            signal = analysis['strategy_signal']
            
            if signal['action'] == 'hold':
                return {"status": "no_signal", "message": "No trading signal generated"}
            
            # Log the signal
            trading_logger.log_trade_signal(symbol, signal)
            
            # Calculate position size
            position_size = self.portfolio.calculate_position_size(signal['confidence'])
            
            # Check risk management
            can_trade, reason = self.portfolio.can_open_position(position_size)
            if not can_trade:
                trading_logger.log_risk_event("TRADE_BLOCKED", reason)
                return {"status": "blocked", "message": reason}
            
            # Check for existing position
            existing_position = self.portfolio.get_position_by_symbol(symbol)
            if existing_position:
                return {"status": "exists", "message": f"Position already exists for {symbol}"}
            
            # Execute trade (simulated for testnet)
            position = Position(
                symbol=symbol,
                side=signal['action'],
                quantity=position_size / signal['entry_price'],
                entry_price=signal['entry_price'],
                stop_loss=signal.get('stop_loss'),
                take_profit=signal.get('take_profit')
            )
            
            self.portfolio.add_position(position)
            
            # Log and broadcast
            trading_logger.log_position_opened(symbol, signal['action'], position.quantity, signal['entry_price'])
            
            if websocket_manager:
                portfolio_data = self.portfolio.get_portfolio_summary()
                await websocket_manager.send_portfolio_update(portfolio_data)
            
            return {
                "status": "success",
                "position": position.to_dict(),
                "message": f"Position opened for {symbol}"
            }
            
        except Exception as e:
            logger.error(f"Error executing position: {e}")
            raise HTTPException(status_code=500, detail=f"Position execution failed: {str(e)}")
    
    async def close_position(self, symbol: str) -> Dict:
        """Close an existing position."""
        try:
            # Get current price
            ticker = self.binance_client.get_symbol_ticker(symbol)
            current_price = float(ticker['price'])
            
            # Close position
            closed_position = self.portfolio.close_position(symbol, current_price)
            
            if not closed_position:
                return {"status": "not_found", "message": f"No open position found for {symbol}"}
            
            # Log and broadcast
            trading_logger.log_position_closed(
                symbol, closed_position.side, closed_position.quantity,
                current_price, closed_position.pnl
            )
            
            if websocket_manager:
                portfolio_data = self.portfolio.get_portfolio_summary()
                await websocket_manager.send_portfolio_update(portfolio_data)
            
            return {
                "status": "success",
                "position": closed_position.to_dict(),
                "message": f"Position closed for {symbol}"
            }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            raise HTTPException(status_code=500, detail=f"Position closing failed: {str(e)}")
    
    async def monitor_positions(self):
        """Background task to monitor positions and execute exits."""
        try:
            open_positions = self.portfolio.get_open_positions()
            
            for position in open_positions:
                # Get current price
                ticker = self.binance_client.get_symbol_ticker(position.symbol)
                current_price = float(ticker['price'])
                
                # Update PnL
                position.update_pnl(current_price)
                
                # Check exit conditions (simplified)
                should_exit = False
                
                # Stop loss/take profit check
                if position.side == 'buy':
                    if position.stop_loss and current_price <= position.stop_loss:
                        should_exit = True
                    elif position.take_profit and current_price >= position.take_profit:
                        should_exit = True
                else:  # sell position
                    if position.stop_loss and current_price >= position.stop_loss:
                        should_exit = True
                    elif position.take_profit and current_price <= position.take_profit:
                        should_exit = True
                
                if should_exit:
                    await self.close_position(position.symbol)
                    
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")

# Initialize WebSocket manager
websocket_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global trading_bot, scheduler
    
    # Startup
    logger.info("Starting up trading bot API server...")
    
    # Initialize trading bot
    trading_bot = TradingBotAPI()
    if not await trading_bot.initialize():
        logger.error("Failed to initialize trading bot")
        raise RuntimeError("Trading bot initialization failed")
    
    # Start scheduler for background tasks
    scheduler = AsyncIOScheduler()
    
    # Add monitoring task (every 30 seconds)
    scheduler.add_job(
        trading_bot.monitor_positions,
        trigger=IntervalTrigger(seconds=30),
        id='monitor_positions',
        replace_existing=True
    )
    
    # Add market analysis task for default symbol (every 60 seconds)
    async def analyze_default_symbol():
        try:
            await trading_bot.analyze_market(Config.DEFAULT_SYMBOL)
        except Exception as e:
            logger.error(f"Error in scheduled analysis: {e}")
    
    scheduler.add_job(
        analyze_default_symbol,
        trigger=IntervalTrigger(seconds=60),
        id='analyze_market',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Background tasks started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down trading bot API server...")
    if scheduler:
        scheduler.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Cryptocurrency Trading Bot API",
    description="REST API for algorithmic cryptocurrency trading with real-time WebSocket updates",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway and monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "trading_mode": Config.TRADING_MODE
    }

# Market analysis endpoints
@app.get("/api/analyze/{symbol}", response_model=AnalysisResponse)
async def analyze_symbol(symbol: str):
    """Analyze market data for a specific symbol."""
    analysis = await trading_bot.analyze_market(symbol.upper())
    
    return AnalysisResponse(
        symbol=analysis['symbol'],
        current_price=analysis['market_summary']['current_price'],
        price_change_24h=analysis['market_summary']['price_change_24h'],
        rsi=analysis['market_summary']['rsi'],
        macd=analysis['market_summary']['macd'],
        signal=analysis['strategy_signal'],
        trend=analysis['trend_analysis'],
        timestamp=analysis['timestamp']
    )

# Portfolio endpoints
@app.get("/api/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """Get current portfolio status."""
    summary = trading_bot.portfolio.get_portfolio_summary()
    
    return PortfolioResponse(
        initial_balance=summary['initial_balance'],
        current_balance=summary['current_balance'],
        unrealized_pnl=summary['unrealized_pnl'],
        portfolio_value=summary['portfolio_value'],
        open_positions=summary['open_positions'],
        performance_metrics=summary['performance_metrics']
    )

@app.get("/api/positions", response_model=List[PositionResponse])
async def get_positions():
    """Get all open positions."""
    positions = trading_bot.portfolio.get_open_positions()
    
    return [
        PositionResponse(
            symbol=pos.symbol,
            side=pos.side,
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            pnl=pos.pnl,
            status=pos.status
        )
        for pos in positions
    ]

# Trading endpoints
@app.post("/api/positions")
async def open_position(position_request: PositionRequest):
    """Open a new trading position."""
    result = await trading_bot.execute_position(
        position_request.symbol.upper(),
        position_request.strategy
    )
    return result

@app.delete("/api/positions/{symbol}")
async def close_position(symbol: str):
    """Close an existing position."""
    result = await trading_bot.close_position(symbol.upper())
    return result

# Strategy endpoints
@app.get("/api/strategies")
async def get_strategies():
    """Get available trading strategies."""
    strategies = trading_bot.strategy_manager.get_available_strategies()
    return {"strategies": strategies}

@app.post("/api/strategies/{strategy_name}")
async def set_strategy(strategy_name: str):
    """Set active trading strategy."""
    try:
        trading_bot.strategy_manager.set_active_strategy(strategy_name)
        return {"status": "success", "active_strategy": strategy_name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/ws/live-data")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data and updates."""
    await websocket_manager.connect(websocket)
    
    try:
        # Send initial data
        if Config.DEFAULT_SYMBOL in trading_bot.last_analysis:
            analysis = trading_bot.last_analysis[Config.DEFAULT_SYMBOL]
            await websocket_manager.send_personal_message({
                "type": "initial_data",
                "analysis": analysis
            }, websocket)
        
        # Send initial portfolio data
        portfolio_data = trading_bot.portfolio.get_portfolio_summary()
        await websocket_manager.send_personal_message({
            "type": "portfolio_update",
            "data": portfolio_data
        }, websocket)
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "subscribe":
                    symbol = message.get("symbol", Config.DEFAULT_SYMBOL)
                    # Trigger analysis for subscribed symbol
                    analysis = await trading_bot.analyze_market(symbol)
                    await websocket_manager.send_personal_message({
                        "type": "analysis_update",
                        "analysis": analysis
                    }, websocket)
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received from WebSocket")
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        websocket_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )