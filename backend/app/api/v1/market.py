"""
Market data API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.market import MarketData, KlineData, OrderBook, Timeframe
from app.services.binance_service import get_binance_service

router = APIRouter()


@router.get("/{symbol}", response_model=MarketData)
async def get_market_data(symbol: str):
    """Get current market data for a symbol"""
    try:
        service = await get_binance_service()
        market_data = await service.get_market_data(symbol.upper())
        return market_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/klines", response_model=List[KlineData])
async def get_klines(
    symbol: str,
    interval: Timeframe = Query(Timeframe.ONE_MINUTE, description="Kline interval"),
    limit: int = Query(500, ge=1, le=1000, description="Number of klines to return")
):
    """Get kline/candlestick data for a symbol"""
    try:
        service = await get_binance_service()
        klines = await service.get_klines(symbol.upper(), interval.value, limit)
        return klines
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/orderbook", response_model=OrderBook)
async def get_order_book(
    symbol: str,
    limit: int = Query(20, ge=5, le=100, description="Order book depth")
):
    """Get order book for a symbol"""
    try:
        service = await get_binance_service()
        order_book = await service.get_order_book(symbol.upper(), limit)
        return order_book
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/trades")
async def get_recent_trades(
    symbol: str,
    limit: int = Query(100, ge=1, le=500, description="Number of trades to return")
):
    """Get recent trades for a symbol"""
    try:
        service = await get_binance_service()
        trades = await service.get_recent_trades(symbol.upper(), limit)
        return trades
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=List[MarketData])
async def get_batch_market_data(symbols: List[str]):
    """Get market data for multiple symbols"""
    if len(symbols) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 symbols allowed per request")
    
    try:
        service = await get_binance_service()
        market_data_list = []
        
        for symbol in symbols:
            try:
                market_data = await service.get_market_data(symbol.upper())
                market_data_list.append(market_data)
            except Exception as e:
                # Log error but continue with other symbols
                print(f"Error fetching data for {symbol}: {e}")
                
        return market_data_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))