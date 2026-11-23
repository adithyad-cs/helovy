/** E-03 sign-in, E-04 sign-out, E-05 session context (docs/07 §4). */
import { useQuery, type QueryClient } from '@tanstack/react-query'

import { ApiError, apiRequest, setCsrfToken } from './http'
import { queryKeys } from './queryKeys'

export interface SessionInfo {
  user: { id: string; email: string; display_name: string }
  organization: { id: string; name: string }
  role: 'owner'
  business: { id: string; legal_name: string } | null
  csrf_token: string
  session_expires_at: string
}

/** `null` means "not signed in"; any other failure is an error. */
export async function fetchMe(): Promise<SessionInfo | null> {
  try {
    const { data } = await apiRequest<SessionInfo>('/api/v1/auth/me')
    setCsrfToken(data.csrf_token)
    return data
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      setCsrfToken(null)
      return null
    }
    throw error
  }
}

export function useMe() {
  return useQuery({ queryKey: queryKeys.me, queryFn: fetchMe, staleTime: 60_000, retry: false })
}

export async function signIn(email: string, password: string): Promise<SessionInfo> {
  const { data } = await apiRequest<SessionInfo>('/api/v1/auth/login', {
    method: 'POST',
    body: { email, password },
  })
  setCsrfToken(data.csrf_token)
  return data
}

export async function signOut(queryClient: QueryClient): Promise<void> {
  try {
    await apiRequest<void>('/api/v1/auth/logout', { method: 'POST' })
  } catch (error) {
    // Already signed out (401) or the token went stale (403): the local state is cleared anyway.
    if (!(error instanceof ApiError) || ![401, 403].includes(error.status)) throw error
  } finally {
    setCsrfToken(null)
  }
  queryClient.clear()
  queryClient.setQueryData(queryKeys.me, null)
}

/** Set when a request is refused because the session ended, so /login can say so. */
let sessionEnded = false

export function markSessionEnded(queryClient: QueryClient): void {
  sessionEnded = true
  setCsrfToken(null)
  queryClient.setQueryData(queryKeys.me, null)
}

export function isSessionEnded(): boolean {
  return sessionEnded
}

export function clearSessionEnded(): void {
  sessionEnded = false
}
