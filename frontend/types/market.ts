export interface Symbol {
  symbol: string
  base_asset: string
  quote_asset: string
  status: string
  is_spot_trading_allowed: boolean
  is_margin_trading_allowed: boolean
  display_name?: string
}

export interface MarketData {
  symbol: string
  current_price: number
  timestamp: string
  volume_24h: number
  high_24h: number
  low_24h: number
  price_change_24h: number
  price_change_percent_24h: number
  bid_price?: number
  ask_price?: number
  last_trade_price?: number
}

export interface KlineData {
  open_time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  close_time: number
  quote_volume: number
  trades: number
  taker_buy_base_volume: number
  taker_buy_quote_volume: number
}

export interface OrderBookEntry {
  price: number
  quantity: number
}

export interface OrderBook {
  symbol: string
  bids: OrderBookEntry[]
  asks: OrderBookEntry[]
  last_update_id: number
  timestamp: string
}

export type Timeframe = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1d'

export interface Tab {
  id: string
  symbol: string
  timeframe: Timeframe
  active: boolean
}