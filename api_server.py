#!/usr/bin/env python3
"""
FastAPI REST API Server for Cryptocurrency Trading Bot
Refactored to use the core trading service
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Import our core service and models
from trading_service import TradingService, create_trading_service
from models import (
    AnalysisResponse, PortfolioResponse, PositionResponse, StrategiesResponse,
    PositionRequest, StrategyRequest, TradeExecutionResult, HealthCheckResponse,
    MarketUpdateMessage, SignalUpdateMessage, PortfolioUpdateMessage,
    WebSocketSubscribeMessage, ErrorResponse, TradingMode
)
from events import get_event_subscriber, EventSubscriber
from config import Config
from logger import trading_logger, get_logger

# Initialize logger
logger = get_logger("api_server")

# Global instances
trading_service: Optional[TradingService] = None
scheduler: Optional[AsyncIOScheduler] = None
websocket_manager = None

class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.event_subscriber: Optional[EventSubscriber] = None
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send initial data
        await self._send_initial_data(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def _send_initial_data(self, websocket: WebSocket):
        """Send initial data to newly connected WebSocket."""
        try:
            if trading_service:
                # Send portfolio data
                portfolio = trading_service.get_portfolio_summary()
                portfolio_message = PortfolioUpdateMessage(
                    data=portfolio,
                    timestamp=datetime.now()
                )
                await self.send_personal_message(portfolio_message.dict(), websocket)
                
                # Send last analysis if available
                last_analysis = trading_service.get_last_analysis(Config.DEFAULT_SYMBOL)
                if last_analysis:
                    market_message = MarketUpdateMessage(
                        symbol=last_analysis.symbol,
                        data=last_analysis.market_summary,
                        timestamp=datetime.now()
                    )
                    await self.send_personal_message(market_message.dict(), websocket)
                    
                    signal_message = SignalUpdateMessage(
                        symbol=last_analysis.symbol,
                        signal=last_analysis.strategy_signal,
                        timestamp=datetime.now()
                    )
                    await self.send_personal_message(signal_message.dict(), websocket)
                    
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """Send message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected WebSockets."""
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
    
    def setup_event_handlers(self):
        """Setup event handlers to broadcast updates."""
        if not self.event_subscriber:
            self.event_subscriber = get_event_subscriber()
        
        async def on_market_data(event):
            message = MarketUpdateMessage(
                symbol=event.symbol,
                data={"current_price": event.price, "volume": event.volume or 0},
                timestamp=event.timestamp
            )
            await self.broadcast(message.dict())
        
        async def on_signal_generated(event):
            message = SignalUpdateMessage(
                symbol=event.symbol,
                signal=event.signal,
                timestamp=event.timestamp
            )
            await self.broadcast(message.dict())
        
        async def on_position_opened(event):
            # Send updated portfolio
            if trading_service:
                portfolio = trading_service.get_portfolio_summary()
                message = PortfolioUpdateMessage(
                    data=portfolio,
                    timestamp=datetime.now()
                )
                await self.broadcast(message.dict())
        
        async def on_position_closed(event):
            # Send updated portfolio
            if trading_service:
                portfolio = trading_service.get_portfolio_summary()
                message = PortfolioUpdateMessage(
                    data=portfolio,
                    timestamp=datetime.now()
                )
                await self.broadcast(message.dict())
        
        # Subscribe to events
        self.event_subscriber.on_market_data(on_market_data, async_handler=True)
        self.event_subscriber.on_signal_generated(on_signal_generated, async_handler=True)
        self.event_subscriber.on_position_opened(on_position_opened, async_handler=True)
        self.event_subscriber.on_position_closed(on_position_closed, async_handler=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global trading_service, scheduler, websocket_manager
    
    # Startup
    logger.info("Starting up trading bot API server...")
    
    # Initialize trading service
    trading_service = create_trading_service()
    if not await trading_service.initialize():
        logger.error("Failed to initialize trading service")
        raise RuntimeError("Trading service initialization failed")
    
    # Initialize WebSocket manager
    websocket_manager = WebSocketManager()
    websocket_manager.setup_event_handlers()
    
    # Start scheduler for background tasks
    scheduler = AsyncIOScheduler()
    
    # Add monitoring task (every 30 seconds)
    scheduler.add_job(
        trading_service.monitor_positions,
        trigger=IntervalTrigger(seconds=30),
        id='monitor_positions',
        replace_existing=True
    )
    
    # Add market analysis task for default symbol (every 60 seconds)
    async def analyze_default_symbol():
        try:
            await trading_service.analyze_market(Config.DEFAULT_SYMBOL)
        except Exception as e:
            logger.error(f"Error in scheduled analysis: {e}")
    
    scheduler.add_job(
        analyze_default_symbol,
        trigger=IntervalTrigger(seconds=60),
        id='analyze_market',
        replace_existing=True
    )
    
    # Start monitoring and scheduler
    asyncio.create_task(trading_service.start_monitoring(30))
    scheduler.start()
    logger.info("Background tasks started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down trading bot API server...")
    if scheduler:
        scheduler.shutdown()
    if trading_service:
        await trading_service.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Cryptocurrency Trading Bot API",
    description="REST API for algorithmic cryptocurrency trading with real-time WebSocket updates",
    version="2.0.0",
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

# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc),
            timestamp=datetime.now()
        ).dict()
    )

# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for Railway and monitoring."""
    if not trading_service or not trading_service.is_initialized:
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version="2.0.0",
            trading_mode=TradingMode(Config.TRADING_MODE)
        )
    
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="2.0.0",
        trading_mode=TradingMode(Config.TRADING_MODE),
        uptime_seconds=trading_service.get_uptime_seconds()
    )

# Market analysis endpoints
@app.get("/api/analyze/{symbol}", response_model=AnalysisResponse)
async def analyze_symbol(symbol: str):
    """Analyze market data for a specific symbol."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading service not available")
    
    try:
        analysis = await trading_service.analyze_market(symbol.upper())
        
        return AnalysisResponse(
            symbol=analysis.symbol,
            current_price=analysis.market_summary.current_price,
            price_change_24h=analysis.market_summary.price_change_24h,
            rsi=analysis.market_summary.rsi,
            macd=analysis.market_summary.macd,
            signal=analysis.strategy_signal,
            trend=analysis.trend_analysis,
            timestamp=analysis.timestamp
        )
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Portfolio endpoints
@app.get("/api/portfolio", response_model=PortfolioResponse)
async def get_portfolio():
    """Get current portfolio status."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading service not available")
    
    try:
        summary = trading_service.get_portfolio_summary()
        
        return PortfolioResponse(
            initial_balance=summary.initial_balance,
            current_balance=summary.current_balance,
            unrealized_pnl=summary.unrealized_pnl,
            portfolio_value=summary.portfolio_value,
            open_positions=summary.open_positions,
            performance_metrics=summary.performance_metrics
        )
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        raise HTTPException(status_code=500, detail=f"Portfolio fetch failed: {str(e)}")

@app.get("/api/positions", response_model=List[PositionResponse])
async def get_positions():
    """Get all open positions."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading service not available")
    
    try:
        positions = trading_service.get_open_positions()
        
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
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=f"Positions fetch failed: {str(e)}")

# Trading endpoints
@app.post("/api/positions", response_model=TradeExecutionResult)
async def open_position(position_request: PositionRequest):
    """Open a new trading position."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading service not available")
    
    try:
        result = await trading_service.execute_position(
            position_request.symbol.upper(),
            position_request.strategy
        )
        return result
    except Exception as e:
        logger.error(f"Error opening position: {e}")
        raise HTTPException(status_code=500, detail=f"Position execution failed: {str(e)}")

@app.delete("/api/positions/{symbol}", response_model=TradeExecutionResult)
async def close_position(symbol: str):
    """Close an existing position."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading service not available")
    
    try:
        result = await trading_service.close_position(symbol.upper())
        return result
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(status_code=500, detail=f"Position closing failed: {str(e)}")

# Strategy endpoints
@app.get("/api/strategies", response_model=StrategiesResponse)
async def get_strategies():
    """Get available trading strategies."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading service not available")
    
    try:
        strategies = trading_service.get_available_strategies()
        active_strategy = trading_service.get_active_strategy()
        
        return StrategiesResponse(
            strategies=strategies,
            active_strategy=active_strategy
        )
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail=f"Strategies fetch failed: {str(e)}")

@app.post("/api/strategies/{strategy_name}")
async def set_strategy(strategy_name: str):
    """Set active trading strategy."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading service not available")
    
    try:
        trading_service.set_active_strategy(strategy_name)
        return {"status": "success", "active_strategy": strategy_name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error setting strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Strategy change failed: {str(e)}")

# Configuration endpoints
@app.get("/api/config")
async def get_config():
    """Get current trading configuration."""
    if not trading_service:
        raise HTTPException(status_code=503, detail="Trading service not available")
    
    try:
        config = trading_service.get_config()
        return config.dict()
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(status_code=500, detail=f"Config fetch failed: {str(e)}")

# WebSocket endpoint for real-time updates
@app.websocket("/ws/live-data")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time market data and updates."""
    if not websocket_manager:
        await websocket.close(code=1013, reason="Service not available")
        return
    
    await websocket_manager.connect(websocket)
    
    try:
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
                    if trading_service:
                        analysis = await trading_service.analyze_market(symbol)
                        analysis_message = {
                            "type": "analysis_update",
                            "analysis": analysis.dict(),
                            "timestamp": datetime.now().isoformat()
                        }
                        await websocket_manager.send_personal_message(analysis_message, websocket)
                
                elif message.get("type") == "ping":
                    # Respond to ping
                    pong_message = {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket_manager.send_personal_message(pong_message, websocket)
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received from WebSocket")
                error_message = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket_manager.send_personal_message(error_message, websocket)
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        websocket_manager.disconnect(websocket)

# Additional utility endpoints
@app.get("/api/status")
async def get_status():
    """Get detailed system status."""
    if not trading_service:
        return {"status": "service_unavailable", "message": "Trading service not initialized"}
    
    try:
        portfolio = trading_service.get_portfolio_summary()
        uptime = trading_service.get_uptime_seconds()
        
        return {
            "status": "operational",
            "uptime_seconds": uptime,
            "trading_mode": Config.TRADING_MODE,
            "active_strategy": trading_service.get_active_strategy(),
            "is_monitoring": trading_service.is_monitoring,
            "portfolio_value": portfolio.portfolio_value,
            "open_positions": portfolio.open_positions,
            "connected_websockets": len(websocket_manager.active_connections) if websocket_manager else 0,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )