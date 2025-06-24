'use client'

import { WebSocketProvider } from '@/contexts/WebSocketContext'
import { MarketDataProvider } from '@/contexts/MarketDataContext'
import { TabsProvider } from '@/contexts/TabsContext'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <WebSocketProvider>
        <MarketDataProvider>
          <TabsProvider>
            {children}
            <Toaster
              position="top-right"
              toastOptions={{
                style: {
                  background: '#2B3139',
                  color: '#fff',
                },
              }}
            />
          </TabsProvider>
        </MarketDataProvider>
      </WebSocketProvider>
    </QueryClientProvider>
  )
}