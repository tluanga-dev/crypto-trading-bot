'use client'

import React, { useState, useEffect, useCallback } from 'react'
import * as Select from '@radix-ui/react-select'
import { ChevronDown, Search, Star, X } from 'lucide-react'
import { useMarketData } from '@/contexts/MarketDataContext'
import { useTabs } from '@/contexts/TabsContext'
import { Symbol } from '@/types/market'
import { clsx } from 'clsx'

export function CryptoSelector() {
  const { symbols, selectedSymbol, selectSymbol } = useMarketData()
  const { addTab } = useTabs()
  const [searchQuery, setSearchQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [favorites, setFavorites] = useState<Set<string>>(new Set())

  // Load favorites from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('crypto-favorites')
    if (saved) {
      setFavorites(new Set(JSON.parse(saved)))
    }
  }, [])

  // Save favorites to localStorage
  const toggleFavorite = useCallback((symbol: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setFavorites(prev => {
      const newFavorites = new Set(prev)
      if (newFavorites.has(symbol)) {
        newFavorites.delete(symbol)
      } else {
        newFavorites.add(symbol)
      }
      localStorage.setItem('crypto-favorites', JSON.stringify(Array.from(newFavorites)))
      return newFavorites
    })
  }, [])

  const filteredSymbols = symbols.filter(symbol => 
    symbol.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    symbol.base_asset.toLowerCase().includes(searchQuery.toLowerCase()) ||
    symbol.quote_asset.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const favoriteSymbols = filteredSymbols.filter(s => favorites.has(s.symbol))
  const regularSymbols = filteredSymbols.filter(s => !favorites.has(s.symbol))

  const handleSelect = (symbol: string) => {
    selectSymbol(symbol)
    addTab(symbol)
    setIsOpen(false)
    setSearchQuery('')
  }

  return (
    <div className="relative">
      <Select.Root open={isOpen} onOpenChange={setIsOpen}>
        <Select.Trigger
          className={clsx(
            "flex items-center justify-between gap-2 px-4 py-2 rounded-lg",
            "bg-crypto-gray hover:bg-crypto-light-gray transition-colors",
            "border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500",
            "min-w-[200px]"
          )}
        >
          <span className="font-medium">{selectedSymbol}</span>
          <ChevronDown className="w-4 h-4" />
        </Select.Trigger>

        <Select.Portal>
          <Select.Content
            className="bg-crypto-gray border border-gray-700 rounded-lg shadow-xl z-50 w-[300px] max-h-[400px] overflow-hidden"
            position="popper"
            sideOffset={5}
          >
            {/* Search Input */}
            <div className="sticky top-0 bg-crypto-gray border-b border-gray-700 p-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search symbols..."
                  className="w-full pl-10 pr-10 py-2 bg-crypto-light-gray rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  onClick={(e) => e.stopPropagation()}
                />
                {searchQuery && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setSearchQuery('')
                    }}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2"
                  >
                    <X className="w-4 h-4 text-gray-400 hover:text-white" />
                  </button>
                )}
              </div>
            </div>

            {/* Symbol List */}
            <Select.Viewport className="max-h-[300px] overflow-y-auto">
              {favoriteSymbols.length > 0 && (
                <>
                  <div className="px-3 py-2 text-xs text-gray-400 uppercase">Favorites</div>
                  {favoriteSymbols.map((symbol) => (
                    <SymbolItem
                      key={symbol.symbol}
                      symbol={symbol}
                      isFavorite={true}
                      onSelect={handleSelect}
                      onToggleFavorite={toggleFavorite}
                    />
                  ))}
                </>
              )}

              {regularSymbols.length > 0 && (
                <>
                  {favoriteSymbols.length > 0 && (
                    <div className="px-3 py-2 text-xs text-gray-400 uppercase">All Symbols</div>
                  )}
                  {regularSymbols.map((symbol) => (
                    <SymbolItem
                      key={symbol.symbol}
                      symbol={symbol}
                      isFavorite={false}
                      onSelect={handleSelect}
                      onToggleFavorite={toggleFavorite}
                    />
                  ))}
                </>
              )}

              {filteredSymbols.length === 0 && (
                <div className="px-3 py-8 text-center text-gray-400">
                  No symbols found
                </div>
              )}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
    </div>
  )
}

interface SymbolItemProps {
  symbol: Symbol
  isFavorite: boolean
  onSelect: (symbol: string) => void
  onToggleFavorite: (symbol: string, e: React.MouseEvent) => void
}

function SymbolItem({ symbol, isFavorite, onSelect, onToggleFavorite }: SymbolItemProps) {
  return (
    <Select.Item
      value={symbol.symbol}
      className={clsx(
        "flex items-center justify-between px-3 py-2",
        "hover:bg-crypto-light-gray cursor-pointer transition-colors",
        "focus:bg-crypto-light-gray focus:outline-none"
      )}
      onClick={() => onSelect(symbol.symbol)}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={(e) => onToggleFavorite(symbol.symbol, e)}
          className="text-gray-400 hover:text-yellow-500 transition-colors"
        >
          <Star className={clsx("w-4 h-4", isFavorite && "fill-yellow-500 text-yellow-500")} />
        </button>
        <div>
          <div className="font-medium">{symbol.symbol}</div>
          <div className="text-xs text-gray-400">
            {symbol.base_asset} / {symbol.quote_asset}
          </div>
        </div>
      </div>
    </Select.Item>
  )
}