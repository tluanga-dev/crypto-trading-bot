'use client'

import React, { useEffect, useState } from 'react'
import { useMarketData } from '@/contexts/MarketDataContext'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { clsx } from 'clsx'

interface PriceDisplayProps {
  symbol: string
}

export function PriceDisplay({ symbol }: PriceDisplayProps) {
  const { marketData } = useMarketData()
  const data = marketData[symbol]
  const [priceChange, setPriceChange] = useState<'up' | 'down' | null>(null)
  const [prevPrice, setPrevPrice] = useState<number | null>(null)

  useEffect(() => {
    if (data?.current_price && prevPrice !== null) {
      if (data.current_price > prevPrice) {
        setPriceChange('up')
      } else if (data.current_price < prevPrice) {
        setPriceChange('down')
      }
      
      // Reset price change indicator after animation
      const timeout = setTimeout(() => setPriceChange(null), 500)
      return () => clearTimeout(timeout)
    }
    setPrevPrice(data?.current_price || null)
  }, [data?.current_price])

  if (!data) {
    return (
      <div className="flex items-center gap-4 p-4 bg-crypto-gray rounded-lg animate-pulse">
        <div className="flex-1">
          <div className="h-4 bg-crypto-light-gray rounded w-20 mb-2"></div>
          <div className="h-8 bg-crypto-light-gray rounded w-32"></div>
        </div>
        <div className="text-right">
          <div className="h-4 bg-crypto-light-gray rounded w-16 mb-2"></div>
          <div className="h-4 bg-crypto-light-gray rounded w-20"></div>
        </div>
      </div>
    )
  }

  const isPositive = data.price_change_24h > 0
  const changeIcon = isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />
  const changeColor = isPositive ? 'text-crypto-green' : 'text-crypto-red'

  return (
    <div className="flex items-center justify-between p-4 bg-crypto-gray rounded-lg">
      <div>
        <div className="text-sm text-gray-400 mb-1">{symbol}</div>
        <div className={clsx(
          "text-2xl font-bold transition-all duration-300",
          priceChange === 'up' && 'price-up',
          priceChange === 'down' && 'price-down'
        )}>
          ${formatPrice(data.current_price)}
        </div>
      </div>
      
      <div className="text-right">
        <div className={clsx("flex items-center gap-1 justify-end", changeColor)}>
          {changeIcon}
          <span className="font-medium">
            {data.price_change_percent_24h.toFixed(2)}%
          </span>
        </div>
        <div className="text-sm text-gray-400">
          24h Volume: ${formatVolume(data.volume_24h)}
        </div>
      </div>
    </div>
  )
}

function formatPrice(price: number): string {
  if (price >= 1) {
    return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  } else if (price >= 0.01) {
    return price.toFixed(4)
  } else {
    return price.toFixed(8)
  }
}

function formatVolume(volume: number): string {
  if (volume >= 1e9) {
    return `${(volume / 1e9).toFixed(2)}B`
  } else if (volume >= 1e6) {
    return `${(volume / 1e6).toFixed(2)}M`
  } else if (volume >= 1e3) {
    return `${(volume / 1e3).toFixed(2)}K`
  } else {
    return volume.toFixed(2)
  }
}