'use client'

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { Symbol, MarketData, KlineData, Timeframe } from '@/types/market'
import { PriceUpdateMessage, KlineUpdateMessage } from '@/types/websocket'
import { useWebSocket } from './WebSocketContext'
import axios from 'axios'

interface MarketDataContextType {
  // State
  symbols: Symbol[]
  selectedSymbol: string
  marketData: Record<string, MarketData>
  klines: Record<string, Record<Timeframe, KlineData[]>>
  loading: boolean
  error: string | null
  
  // Actions
  loadSymbols: () => Promise<void>
  selectSymbol: (symbol: string) => void
  loadMarketData: (symbol: string) => Promise<void>
  loadKlines: (symbol: string, timeframe: Timeframe) => Promise<void>
  updateMarketData: (symbol: string, data: Partial<MarketData>) => void
  updateKline: (symbol: string, timeframe: Timeframe, kline: KlineData) => void
}

const MarketDataContext = createContext<MarketDataContextType | undefined>(undefined)

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function MarketDataProvider({ children }: { children: React.ReactNode }) {
  const [symbols, setSymbols] = useState<Symbol[]>([])
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT')
  const [marketData, setMarketData] = useState<Record<string, MarketData>>({})
  const [klines, setKlines] = useState<Record<string, Record<Timeframe, KlineData[]>>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { addMessageHandler, removeMessageHandler } = useWebSocket()

  // Load symbols from API
  const loadSymbols = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await axios.get(`${API_URL}/api/v1/symbols/popular`)
      setSymbols(response.data)
    } catch (err) {
      setError('Failed to load symbols')
      console.error('Error loading symbols:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Select a symbol
  const selectSymbol = useCallback((symbol: string) => {
    setSelectedSymbol(symbol)
  }, [])

  // Load market data for a symbol
  const loadMarketData = useCallback(async (symbol: string) => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/market/${symbol}`)
      setMarketData(prev => ({
        ...prev,
        [symbol]: response.data
      }))
    } catch (err) {
      console.error(`Error loading market data for ${symbol}:`, err)
    }
  }, [])

  // Load klines for a symbol and timeframe
  const loadKlines = useCallback(async (symbol: string, timeframe: Timeframe) => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/market/${symbol}/klines`, {
        params: { interval: timeframe, limit: 100 }
      })
      
      setKlines(prev => ({
        ...prev,
        [symbol]: {
          ...prev[symbol],
          [timeframe]: response.data
        }
      }))
    } catch (err) {
      console.error(`Error loading klines for ${symbol} ${timeframe}:`, err)
    }
  }, [])

  // Update market data
  const updateMarketData = useCallback((symbol: string, data: Partial<MarketData>) => {
    setMarketData(prev => ({
      ...prev,
      [symbol]: {
        ...prev[symbol],
        ...data,
        timestamp: new Date().toISOString()
      }
    }))
  }, [])

  // Update kline
  const updateKline = useCallback((symbol: string, timeframe: Timeframe, kline: KlineData) => {
    setKlines(prev => {
      const symbolKlines = prev[symbol] || {}
      const timeframeKlines = symbolKlines[timeframe] || []
      
      // Find and update existing kline or add new one
      const existingIndex = timeframeKlines.findIndex(k => k.open_time === kline.open_time)
      
      let newKlines: KlineData[]
      if (existingIndex !== -1) {
        // Update existing kline
        newKlines = [...timeframeKlines]
        newKlines[existingIndex] = kline
      } else {
        // Add new kline and keep only last 100
        newKlines = [...timeframeKlines, kline].slice(-100)
      }
      
      return {
        ...prev,
        [symbol]: {
          ...symbolKlines,
          [timeframe]: newKlines
        }
      }
    })
  }, [])

  // Handle WebSocket messages
  useEffect(() => {
    const handlePriceUpdate = (message: PriceUpdateMessage) => {
      updateMarketData(message.symbol, {
        current_price: message.price,
        volume_24h: message.volume || 0
      })
    }

    const handleKlineUpdate = (message: KlineUpdateMessage) => {
      updateKline(message.symbol, message.interval as Timeframe, message.kline)
    }

    addMessageHandler('price_update', handlePriceUpdate)
    addMessageHandler('kline_update', handleKlineUpdate)

    return () => {
      removeMessageHandler('price_update', handlePriceUpdate)
      removeMessageHandler('kline_update', handleKlineUpdate)
    }
  }, [addMessageHandler, removeMessageHandler, updateMarketData, updateKline])

  // Load initial data
  useEffect(() => {
    loadSymbols()
  }, [loadSymbols])

  return (
    <MarketDataContext.Provider value={{
      symbols,
      selectedSymbol,
      marketData,
      klines,
      loading,
      error,
      loadSymbols,
      selectSymbol,
      loadMarketData,
      loadKlines,
      updateMarketData,
      updateKline
    }}>
      {children}
    </MarketDataContext.Provider>
  )
}

export function useMarketData() {
  const context = useContext(MarketDataContext)
  if (context === undefined) {
    throw new Error('useMarketData must be used within a MarketDataProvider')
  }
  return context
}