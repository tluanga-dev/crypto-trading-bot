'use client'

import { CryptoSelector } from '@/components/ui/CryptoSelector'
import { TabManager } from '@/components/ui/TabManager'
import { ChartContainer } from '@/components/ChartContainer'
import { useWebSocket } from '@/contexts/WebSocketContext'
import { useTabs } from '@/contexts/TabsContext'
import { Wifi, WifiOff } from 'lucide-react'

export default function Home() {
  const { connected } = useWebSocket()
  const { activeTabId } = useTabs()

  return (
    <div className="flex flex-col h-screen bg-crypto-dark">
      {/* Header */}
      <header className="flex items-center justify-between p-4 bg-crypto-gray border-b border-gray-700">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">Crypto Trading Platform</h1>
          <CryptoSelector />
        </div>
        
        <div className="flex items-center gap-2">
          {connected ? (
            <>
              <Wifi className="w-4 h-4 text-green-500" />
              <span className="text-sm text-green-500">Connected</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-red-500" />
              <span className="text-sm text-red-500">Disconnected</span>
            </>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        <TabManager>
          {activeTabId && <ChartContainer tabId={activeTabId} />}
        </TabManager>
      </main>

      {/* Footer */}
      <footer className="p-4 bg-crypto-gray border-t border-gray-700 text-center text-sm text-gray-400">
        Real-time data powered by Binance API
      </footer>
    </div>
  )
}