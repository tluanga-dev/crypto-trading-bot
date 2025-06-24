"""
Symbol-related API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.symbol import Symbol, SymbolList
from app.services.binance_service import get_binance_service

router = APIRouter()


@router.get("/", response_model=SymbolList)
async def get_symbols(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    quote_asset: Optional[str] = Query(None, description="Filter by quote asset (e.g., USDT, BTC)")
):
    """Get list of available trading symbols"""
    try:
        service = await get_binance_service()
        all_symbols = await service.get_all_symbols()
        
        # Filter by quote asset if provided
        if quote_asset:
            all_symbols = [s for s in all_symbols if s.quote_asset == quote_asset.upper()]
        
        # Apply pagination
        total = len(all_symbols)
        symbols = all_symbols[offset:offset + limit]
        
        return SymbolList(symbols=symbols, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=List[Symbol])
async def search_symbols(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=100)
):
    """Search symbols by query"""
    try:
        service = await get_binance_service()
        symbols = await service.search_symbols(q)
        return symbols[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular", response_model=List[Symbol])
async def get_popular_symbols():
    """Get popular trading symbols"""
    # Define popular symbols
    popular_pairs = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
        "SOLUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "MATICUSDT",
        "LTCUSDT", "UNIUSDT", "LINKUSDT", "ATOMUSDT", "XLMUSDT"
    ]
    
    try:
        service = await get_binance_service()
        all_symbols = await service.get_all_symbols()
        
        # Filter for popular symbols
        popular_symbols = [
            symbol for symbol in all_symbols 
            if symbol.symbol in popular_pairs
        ]
        
        # Sort by the order in popular_pairs
        popular_symbols.sort(key=lambda x: popular_pairs.index(x.symbol) if x.symbol in popular_pairs else 999)
        
        return popular_symbols
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}", response_model=Symbol)
async def get_symbol_info(symbol: str):
    """Get detailed information about a specific symbol"""
    try:
        service = await get_binance_service()
        all_symbols = await service.get_all_symbols()
        
        symbol_upper = symbol.upper()
        for s in all_symbols:
            if s.symbol == symbol_upper:
                return s
                
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))