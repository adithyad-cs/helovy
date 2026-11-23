/**
 * The sign-in `next` parameter accepts only same-origin paths beginning with /app, which
 * prevents open redirects (docs/12 §6).
 */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith('/app') || next.startsWith('//') || next.includes('\\')) return '/app'
  try {
    const url = new URL(next, window.location.origin)
    if (url.origin !== window.location.origin) return '/app'
    if (url.pathname !== '/app' && !url.pathname.startsWith('/app/')) return '/app'
    return url.pathname + url.search + url.hash
  } catch {
    return '/app'
  }
}

export function loginPath(next: string, expired: boolean): string {
  const params = new URLSearchParams({ next })
  if (expired) params.set('reason', 'expired')
  return `/login?${params.toString()}`
}
