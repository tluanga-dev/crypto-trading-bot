'use client'

import React, { useEffect, useRef, useState } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData, ColorType } from 'lightweight-charts'
import { useMarketData } from '@/contexts/MarketDataContext'
import { useWebSocket } from '@/contexts/WebSocketContext'
import { KlineData, Timeframe } from '@/types/market'
import { Loader2 } from 'lucide-react'

interface CandlestickChartProps {
  symbol: string
  timeframe: Timeframe
}

export function CandlestickChart({ symbol, timeframe }: CandlestickChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  
  const { klines, loadKlines } = useMarketData()
  const { subscribe, unsubscribe } = useWebSocket()
  const [isLoading, setIsLoading] = useState(true)

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await loadKlines(symbol, timeframe)
      setIsLoading(false)
    }
    loadData()
  }, [symbol, timeframe, loadKlines])

  // Subscribe to WebSocket updates
  useEffect(() => {
    subscribe(symbol, [timeframe])
    
    return () => {
      unsubscribe(symbol)
    }
  }, [symbol, timeframe, subscribe, unsubscribe])

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { type: ColorType.Solid, color: '#0B0E11' },
        textColor: '#D1D4DC',
      },
      grid: {
        vertLines: { color: '#2B3139' },
        horzLines: { color: '#2B3139' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          width: 1,
          color: '#758696',
          style: 3,
        },
        horzLine: {
          width: 1,
          color: '#758696',
          style: 3,
        },
      },
      rightPriceScale: {
        borderColor: '#2B3139',
      },
      timeScale: {
        borderColor: '#2B3139',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#00D395',
      downColor: '#F6465D',
      borderUpColor: '#00D395',
      borderDownColor: '#F6465D',
      wickUpColor: '#00D395',
      wickDownColor: '#F6465D',
    })

    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
    })

    chart.priceScale('').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    })

    chartRef.current = chart
    candlestickSeriesRef.current = candlestickSeries
    volumeSeriesRef.current = volumeSeries

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [])

  // Update chart data
  useEffect(() => {
    const symbolKlines = klines[symbol]?.[timeframe]
    if (!symbolKlines || !candlestickSeriesRef.current || !volumeSeriesRef.current) return

    const candlestickData: CandlestickData[] = symbolKlines.map(kline => ({
      time: Math.floor(kline.open_time / 1000) as any,
      open: kline.open,
      high: kline.high,
      low: kline.low,
      close: kline.close,
    }))

    const volumeData = symbolKlines.map(kline => ({
      time: Math.floor(kline.open_time / 1000) as any,
      value: kline.volume,
      color: kline.close >= kline.open ? '#00D395' : '#F6465D',
    }))

    candlestickSeriesRef.current.setData(candlestickData)
    volumeSeriesRef.current.setData(volumeData)

    // Fit content
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent()
    }
  }, [klines, symbol, timeframe])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[500px] bg-crypto-gray rounded-lg">
        <div className="flex items-center gap-2">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading chart data...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      <div ref={chartContainerRef} className="w-full h-[500px] bg-crypto-dark rounded-lg" />
    </div>
  )
}