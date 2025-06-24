"""
Symbol models
"""
from typing import List, Optional
from pydantic import BaseModel


class Symbol(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    status: str
    is_spot_trading_allowed: bool
    is_margin_trading_allowed: bool
    filters: Optional[dict] = None
    
    @property
    def display_name(self) -> str:
        return f"{self.base_asset}/{self.quote_asset}"


class SymbolInfo(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    base_asset_precision: int
    quote_asset_precision: int
    min_quantity: float
    max_quantity: float
    step_size: float
    min_notional: float
    tick_size: float
    status: str


class SymbolList(BaseModel):
    symbols: List[Symbol]
    total: int


class SymbolSearch(BaseModel):
    query: str
    limit: int = 50
    offset: int = 0