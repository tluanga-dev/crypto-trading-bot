'use client'

import React from 'react'
import * as Tabs from '@radix-ui/react-tabs'
import { Timeframe } from '@/types/market'
import { clsx } from 'clsx'

interface TimeframeSelectorProps {
  activeTimeframe: Timeframe
  onTimeframeChange: (timeframe: Timeframe) => void
}

const timeframes: { value: Timeframe; label: string }[] = [
  { value: '1m', label: '1M' },
  { value: '5m', label: '5M' },
  { value: '15m', label: '15M' },
  { value: '30m', label: '30M' },
  { value: '1h', label: '1H' },
  { value: '4h', label: '4H' },
  { value: '1d', label: '1D' },
]

export function TimeframeSelector({ activeTimeframe, onTimeframeChange }: TimeframeSelectorProps) {
  return (
    <Tabs.Root value={activeTimeframe} onValueChange={(value) => onTimeframeChange(value as Timeframe)}>
      <Tabs.List className="flex items-center gap-1 p-1 bg-crypto-gray rounded-lg">
        {timeframes.map((tf) => (
          <Tabs.Trigger
            key={tf.value}
            value={tf.value}
            className={clsx(
              "px-3 py-1.5 rounded-md text-sm font-medium transition-all",
              "hover:bg-crypto-light-gray",
              "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-crypto-gray",
              "data-[state=active]:bg-blue-600 data-[state=active]:text-white"
            )}
          >
            {tf.label}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
    </Tabs.Root>
  )
}