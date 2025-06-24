"""
WebSocket-related API endpoints
"""
from fastapi import APIRouter, HTTPException
from app.core.binance_ws import get_ws_manager

router = APIRouter()


@router.get("/status")
async def get_websocket_status():
    """Get WebSocket connection status"""
    try:
        ws_manager = await get_ws_manager()
        
        return {
            "active_subscriptions": ws_manager.get_active_subscriptions(),
            "connection_status": ws_manager.get_connection_status()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions")
async def get_active_subscriptions():
    """Get all active WebSocket subscriptions"""
    try:
        ws_manager = await get_ws_manager()
        subscriptions = ws_manager.get_active_subscriptions()
        
        # Format the response
        formatted_subscriptions = []
        for symbol, stream_types in subscriptions.items():
            formatted_subscriptions.append({
                "symbol": symbol,
                "streams": list(stream_types)
            })
            
        return {
            "total_symbols": len(subscriptions),
            "subscriptions": formatted_subscriptions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))