'use client'

import React from 'react'
import * as Tabs from '@radix-ui/react-tabs'
import { X, Plus } from 'lucide-react'
import { useTabs } from '@/contexts/TabsContext'
import { useMarketData } from '@/contexts/MarketDataContext'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'

export function TabManager({ children }: { children: React.ReactNode }) {
  const { tabs, activeTabId, setActiveTab, removeTab, addTab, maxTabs } = useTabs()
  const { selectSymbol, symbols } = useMarketData()

  const handleTabChange = (tabId: string) => {
    const tab = tabs.find(t => t.id === tabId)
    if (tab) {
      setActiveTab(tabId)
      selectSymbol(tab.symbol)
    }
  }

  const handleAddTab = () => {
    if (tabs.length >= maxTabs) {
      toast.error(`Maximum ${maxTabs} tabs allowed`)
      return
    }

    // Find a symbol that's not already open
    const openSymbols = new Set(tabs.map(t => t.symbol))
    const availableSymbol = symbols.find(s => !openSymbols.has(s.symbol))
    
    if (availableSymbol) {
      addTab(availableSymbol.symbol)
    } else {
      toast.error('No more symbols available')
    }
  }

  const handleRemoveTab = (e: React.MouseEvent, tabId: string) => {
    e.stopPropagation()
    if (tabs.length === 1) {
      toast.error('Cannot close the last tab')
      return
    }
    removeTab(tabId)
  }

  if (tabs.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <button
          onClick={handleAddTab}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Tab
        </button>
      </div>
    )
  }

  return (
    <Tabs.Root value={activeTabId || ''} onValueChange={handleTabChange} className="flex flex-col h-full">
      <div className="flex items-center gap-2 p-2 bg-crypto-gray border-b border-gray-700 overflow-x-auto">
        <Tabs.List className="flex items-center gap-1">
          {tabs.map((tab) => (
            <Tabs.Trigger
              key={tab.id}
              value={tab.id}
              className={clsx(
                "group flex items-center gap-2 px-3 py-2 rounded-lg transition-all",
                "hover:bg-crypto-light-gray",
                "focus:outline-none focus:ring-2 focus:ring-blue-500",
                "data-[state=active]:bg-crypto-light-gray data-[state=active]:border-b-2 data-[state=active]:border-blue-500"
              )}
            >
              <span className="text-sm font-medium">{tab.symbol}</span>
              <button
                onClick={(e) => handleRemoveTab(e, tab.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X className="w-3 h-3 hover:text-red-500" />
              </button>
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {tabs.length < maxTabs && (
          <button
            onClick={handleAddTab}
            className="flex items-center justify-center w-8 h-8 rounded-lg hover:bg-crypto-light-gray transition-colors"
            title="Add new tab"
          >
            <Plus className="w-4 h-4" />
          </button>
        )}
      </div>

      {tabs.map((tab) => (
        <Tabs.Content
          key={tab.id}
          value={tab.id}
          className="flex-1 p-4"
          forceMount
          hidden={tab.id !== activeTabId}
        >
          {children}
        </Tabs.Content>
      ))}
    </Tabs.Root>
  )
}