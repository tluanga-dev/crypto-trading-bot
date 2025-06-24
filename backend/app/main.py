"""
Main FastAPI application
"""
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.api.v1 import market, symbols, websocket
from app.services.binance_service import get_binance_service
from app.core.binance_ws import get_ws_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_subscriptions: Dict[str, Set[str]] = {}  # client_id -> set of symbols
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_subscriptions[client_id] = set()
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket, client_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
        logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
        
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            
    async def broadcast(self, message: dict, symbol: Optional[str] = None):
        """Broadcast message to all connected clients or those subscribed to a symbol"""
        disconnected = []
        
        for idx, connection in enumerate(self.active_connections):
            try:
                # If symbol is specified, only send to clients subscribed to that symbol
                if symbol:
                    client_id = self._get_client_id_by_connection(connection)
                    if client_id and symbol in self.client_subscriptions.get(client_id, set()):
                        await connection.send_json(message)
                else:
                    await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
                
        # Remove disconnected clients
        for connection in disconnected:
            self.active_connections.remove(connection)
            
    def _get_client_id_by_connection(self, websocket: WebSocket) -> Optional[str]:
        """Get client ID by WebSocket connection"""
        # This is a simplified implementation
        # In production, you'd maintain a proper mapping
        for client_id, _ in self.client_subscriptions.items():
            return client_id
        return None
        
    def add_subscription(self, client_id: str, symbol: str):
        """Add symbol subscription for a client"""
        if client_id in self.client_subscriptions:
            self.client_subscriptions[client_id].add(symbol)
            
    def remove_subscription(self, client_id: str, symbol: str):
        """Remove symbol subscription for a client"""
        if client_id in self.client_subscriptions:
            self.client_subscriptions[client_id].discard(symbol)


# Global connection manager
manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    logger.info("Starting Crypto Market Data API...")
    
    # Initialize services
    binance_service = await get_binance_service()
    ws_manager = await get_ws_manager()
    
    # Set up WebSocket callbacks
    async def on_price_update(update):
        await manager.broadcast(update.model_dump(), update.symbol)
        
    async def on_kline_update(update):
        await manager.broadcast(update.model_dump(), update.symbol)
        
    async def on_orderbook_update(update):
        await manager.broadcast(update.model_dump(), update.symbol)
        
    async def on_trade_update(update):
        await manager.broadcast(update.model_dump(), update.symbol)
    
    ws_manager.set_callback("price_update", on_price_update)
    ws_manager.set_callback("kline_update", on_kline_update)
    ws_manager.set_callback("orderbook_update", on_orderbook_update)
    ws_manager.set_callback("trade_update", on_trade_update)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Crypto Market Data API...")
    await ws_manager.stop()
    await binance_service.close()


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(symbols.router, prefix=f"{settings.API_V1_STR}/symbols", tags=["symbols"])
app.include_router(market.router, prefix=f"{settings.API_V1_STR}/market", tags=["market"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    ws_manager = await get_ws_manager()
    connection_status = ws_manager.get_connection_status()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "websocket_connections": len(connection_status),
        "active_streams": sum(1 for status in connection_status.values() if status)
    }


# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time market data"""
    await manager.connect(websocket, client_id)
    ws_manager = await get_ws_manager()
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "subscribe":
                symbol = message["symbol"]
                timeframes = message.get("timeframes", ["1m"])
                
                # Add client subscription
                manager.add_subscription(client_id, symbol)
                
                # Subscribe to Binance streams
                await ws_manager.subscribe_ticker(symbol)
                await ws_manager.subscribe_trades(symbol)
                await ws_manager.subscribe_depth(symbol)
                
                # Subscribe to klines for each timeframe
                for timeframe in timeframes:
                    await ws_manager.subscribe_klines(symbol, timeframe)
                
                # Send confirmation
                await manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "symbol": symbol,
                    "timeframes": timeframes,
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
                
            elif message["type"] == "unsubscribe":
                symbol = message["symbol"]
                
                # Remove client subscription
                manager.remove_subscription(client_id, symbol)
                
                # Check if any other clients are subscribed
                still_subscribed = any(
                    symbol in subs 
                    for cid, subs in manager.client_subscriptions.items() 
                    if cid != client_id
                )
                
                # If no other clients need this symbol, unsubscribe from Binance
                if not still_subscribed:
                    await ws_manager.unsubscribe(symbol)
                
                # Send confirmation
                await manager.send_personal_message({
                    "type": "unsubscription_confirmed",
                    "symbol": symbol,
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
                
            elif message["type"] == "ping":
                # Respond to ping
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
        
        # Clean up subscriptions
        symbols_to_check = manager.client_subscriptions.get(client_id, set()).copy()
        for symbol in symbols_to_check:
            still_subscribed = any(
                symbol in subs 
                for cid, subs in manager.client_subscriptions.items() 
                if cid != client_id
            )
            if not still_subscribed:
                await ws_manager.unsubscribe(symbol)
                
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        manager.disconnect(websocket, client_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )