'use client'

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { Tab, Timeframe } from '@/types/market'

interface TabsContextType {
  tabs: Tab[]
  activeTabId: string | null
  maxTabs: number
  
  addTab: (symbol: string) => void
  removeTab: (tabId: string) => void
  setActiveTab: (tabId: string) => void
  updateTab: (tabId: string, updates: Partial<Tab>) => void
  getTabBySymbol: (symbol: string) => Tab | undefined
}

const TabsContext = createContext<TabsContextType | undefined>(undefined)

const MAX_TABS = 10

export function TabsProvider({ children }: { children: React.ReactNode }) {
  const [tabs, setTabs] = useState<Tab[]>([])
  const [activeTabId, setActiveTabId] = useState<string | null>(null)

  // Load tabs from localStorage on mount
  useEffect(() => {
    const savedTabs = localStorage.getItem('crypto-tabs')
    if (savedTabs) {
      try {
        const parsedTabs = JSON.parse(savedTabs)
        setTabs(parsedTabs)
        if (parsedTabs.length > 0) {
          setActiveTabId(parsedTabs[0].id)
        }
      } catch (error) {
        console.error('Error loading saved tabs:', error)
      }
    } else {
      // Create default tab
      const defaultTab: Tab = {
        id: `tab-${Date.now()}`,
        symbol: 'BTCUSDT',
        timeframe: '5m',
        active: true
      }
      setTabs([defaultTab])
      setActiveTabId(defaultTab.id)
    }
  }, [])

  // Save tabs to localStorage whenever they change
  useEffect(() => {
    if (tabs.length > 0) {
      localStorage.setItem('crypto-tabs', JSON.stringify(tabs))
    }
  }, [tabs])

  const addTab = useCallback((symbol: string) => {
    // Check if tab already exists
    const existingTab = tabs.find(tab => tab.symbol === symbol)
    if (existingTab) {
      setActiveTabId(existingTab.id)
      return
    }

    // Check max tabs limit
    if (tabs.length >= MAX_TABS) {
      console.warn(`Maximum number of tabs (${MAX_TABS}) reached`)
      return
    }

    const newTab: Tab = {
      id: `tab-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      symbol,
      timeframe: '5m',
      active: false
    }

    setTabs(prev => [...prev, newTab])
    setActiveTabId(newTab.id)
  }, [tabs])

  const removeTab = useCallback((tabId: string) => {
    setTabs(prev => {
      const newTabs = prev.filter(tab => tab.id !== tabId)
      
      // If we're removing the active tab, activate another one
      if (activeTabId === tabId && newTabs.length > 0) {
        const removedIndex = prev.findIndex(tab => tab.id === tabId)
        const newActiveIndex = Math.min(removedIndex, newTabs.length - 1)
        setActiveTabId(newTabs[newActiveIndex].id)
      } else if (newTabs.length === 0) {
        setActiveTabId(null)
      }
      
      return newTabs
    })
  }, [activeTabId])

  const setActiveTab = useCallback((tabId: string) => {
    setActiveTabId(tabId)
    setTabs(prev => prev.map(tab => ({
      ...tab,
      active: tab.id === tabId
    })))
  }, [])

  const updateTab = useCallback((tabId: string, updates: Partial<Tab>) => {
    setTabs(prev => prev.map(tab => 
      tab.id === tabId ? { ...tab, ...updates } : tab
    ))
  }, [])

  const getTabBySymbol = useCallback((symbol: string) => {
    return tabs.find(tab => tab.symbol === symbol)
  }, [tabs])

  return (
    <TabsContext.Provider value={{
      tabs,
      activeTabId,
      maxTabs: MAX_TABS,
      addTab,
      removeTab,
      setActiveTab,
      updateTab,
      getTabBySymbol
    }}>
      {children}
    </TabsContext.Provider>
  )
}

export function useTabs() {
  const context = useContext(TabsContext)
  if (context === undefined) {
    throw new Error('useTabs must be used within a TabsProvider')
  }
  return context
}