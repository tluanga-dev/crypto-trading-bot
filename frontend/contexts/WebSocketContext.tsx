'use client'

import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'
import { WebSocketMessage, PriceUpdateMessage, KlineUpdateMessage, OrderBookUpdateMessage, TradeUpdateMessage } from '@/types/websocket'

interface WebSocketContextType {
  connected: boolean
  subscriptions: Set<string>
  subscribe: (symbol: string, timeframes: string[]) => void
  unsubscribe: (symbol: string) => void
  send: (message: any) => void
  addMessageHandler: (type: string, handler: (message: any) => void) => void
  removeMessageHandler: (type: string, handler: (message: any) => void) => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [connected, setConnected] = useState(false)
  const [subscriptions] = useState(new Set<string>())
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const messageHandlersRef = useRef<Map<string, Set<(message: any) => void>>>(new Map())
  const clientId = useRef(`client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/ws/${clientId.current}`
    
    try {
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('WebSocket connected')
        setConnected(true)
        
        // Resubscribe to all symbols
        subscriptions.forEach(symbol => {
          const [sym, timeframesStr] = symbol.split(':')
          const timeframes = timeframesStr?.split(',') || ['1m']
          wsRef.current?.send(JSON.stringify({
            type: 'subscribe',
            symbol: sym,
            timeframes
          }))
        })
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          
          // Call all registered handlers for this message type
          const handlers = messageHandlersRef.current.get(message.type)
          if (handlers) {
            handlers.forEach(handler => handler(message))
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected')
        setConnected(false)
        wsRef.current = null
        
        // Attempt to reconnect after 5 seconds
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...')
          connect()
        }, 5000)
      }
    } catch (error) {
      console.error('Error creating WebSocket connection:', error)
    }
  }, [subscriptions])

  useEffect(() => {
    connect()

    // Heartbeat to keep connection alive
    const heartbeatInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)

    return () => {
      clearInterval(heartbeatInterval)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  const subscribe = useCallback((symbol: string, timeframes: string[]) => {
    const subscriptionKey = `${symbol}:${timeframes.join(',')}`
    subscriptions.add(subscriptionKey)
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'subscribe',
        symbol,
        timeframes
      }))
    }
  }, [subscriptions])

  const unsubscribe = useCallback((symbol: string) => {
    // Remove all subscriptions for this symbol
    const toRemove: string[] = []
    subscriptions.forEach(sub => {
      if (sub.startsWith(`${symbol}:`)) {
        toRemove.push(sub)
      }
    })
    toRemove.forEach(sub => subscriptions.delete(sub))
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'unsubscribe',
        symbol
      }))
    }
  }, [subscriptions])

  const send = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  const addMessageHandler = useCallback((type: string, handler: (message: any) => void) => {
    if (!messageHandlersRef.current.has(type)) {
      messageHandlersRef.current.set(type, new Set())
    }
    messageHandlersRef.current.get(type)!.add(handler)
  }, [])

  const removeMessageHandler = useCallback((type: string, handler: (message: any) => void) => {
    const handlers = messageHandlersRef.current.get(type)
    if (handlers) {
      handlers.delete(handler)
      if (handlers.size === 0) {
        messageHandlersRef.current.delete(type)
      }
    }
  }, [])

  return (
    <WebSocketContext.Provider value={{
      connected,
      subscriptions,
      subscribe,
      unsubscribe,
      send,
      addMessageHandler,
      removeMessageHandler
    }}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}