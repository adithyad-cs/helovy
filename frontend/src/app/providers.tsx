import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Tooltip } from 'radix-ui'
import { useState, type ReactNode } from 'react'

import { markSessionEnded } from '../api/auth'
import { ApiError } from '../api/http'
import { ToastProvider } from '../components/ui/Toast'

function isSessionEnd(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401 && error.code === 'unauthenticated'
}

/**
 * Server state lives in TanStack Query (docs/04 §4). Updates are pessimistic (docs/08 §9).
 * Any 401 `unauthenticated` clears the cached session, so the route guard redirects to
 * /login?next=…&reason=expired (docs/08 §22).
 */
function createQueryClient(): QueryClient {
  const client: QueryClient = new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        if (isSessionEnd(error) && query.queryKey[0] !== 'me') markSessionEnded(client)
      },
    }),
    mutationCache: new MutationCache({
      onError: (error) => {
        if (isSessionEnd(error)) markSessionEnded(client)
      },
    }),
    defaultOptions: {
      queries: {
        retry: (failureCount, error) =>
          failureCount < 1 && !(error instanceof ApiError && error.status < 500),
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  })
  return client
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient)
  return (
    <QueryClientProvider client={queryClient}>
      <Tooltip.Provider delayDuration={300}>
        <ToastProvider>{children}</ToastProvider>
      </Tooltip.Provider>
    </QueryClientProvider>
  )
}
