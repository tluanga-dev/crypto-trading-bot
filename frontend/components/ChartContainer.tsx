'use client'

import React, { useState, useEffect } from 'react'
import { useMarketData } from '@/contexts/MarketDataContext'
import { useTabs } from '@/contexts/TabsContext'
import { Timeframe } from '@/types/market'
import { CandlestickChart } from '@/components/ui/CandlestickChart'
import { TimeframeSelector } from '@/components/ui/TimeframeSelector'
import { PriceDisplay } from '@/components/ui/PriceDisplay'

interface ChartContainerProps {
  tabId: string
}

export function ChartContainer({ tabId }: ChartContainerProps) {
  const { tabs, updateTab } = useTabs()
  const { loadMarketData } = useMarketData()
  
  const tab = tabs.find(t => t.id === tabId)
  const [timeframe, setTimeframe] = useState<Timeframe>(tab?.timeframe || '5m')

  useEffect(() => {
    if (tab) {
      loadMarketData(tab.symbol)
    }
  }, [tab, loadMarketData])

  const handleTimeframeChange = (newTimeframe: Timeframe) => {
    setTimeframe(newTimeframe)
    if (tab) {
      updateTab(tab.id, { timeframe: newTimeframe })
    }
  }

  if (!tab) {
    return <div>Tab not found</div>
  }

  return (
    <div className="space-y-4">
      <PriceDisplay symbol={tab.symbol} />
      
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{tab.symbol} Chart</h2>
        <TimeframeSelector
          activeTimeframe={timeframe}
          onTimeframeChange={handleTimeframeChange}
        />
      </div>
      
      <CandlestickChart symbol={tab.symbol} timeframe={timeframe} />
    </div>
  )
}