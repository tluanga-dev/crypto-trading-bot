export type WebSocketMessageType = 
  | 'subscribe'
  | 'unsubscribe'
  | 'ping'
  | 'pong'
  | 'price_update'
  | 'kline_update'
  | 'orderbook_update'
  | 'trade_update'
  | 'subscription_confirmed'
  | 'unsubscription_confirmed'

export interface WebSocketMessage {
  type: WebSocketMessageType
  timestamp: string
}

export interface SubscribeMessage extends WebSocketMessage {
  type: 'subscribe'
  symbol: string
  timeframes: string[]
}

export interface UnsubscribeMessage extends WebSocketMessage {
  type: 'unsubscribe'
  symbol: string
}

export interface PriceUpdateMessage extends WebSocketMessage {
  type: 'price_update'
  symbol: string
  price: number
  volume?: number
}

export interface KlineUpdateMessage extends WebSocketMessage {
  type: 'kline_update'
  symbol: string
  interval: string
  kline: {
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
}

export interface OrderBookUpdateMessage extends WebSocketMessage {
  type: 'orderbook_update'
  symbol: string
  bids: [number, number][]
  asks: [number, number][]
}

export interface TradeUpdateMessage extends WebSocketMessage {
  type: 'trade_update'
  symbol: string
  price: number
  quantity: number
  is_buyer_maker: boolean
}