import { Navigate, Outlet, useLocation } from 'react-router'

import { isSessionEnded, useMe } from '../api/auth'
import { ErrorState } from '../components/ui/States'
import { Spinner } from '../components/ui/Spinner'
import { loginPath } from '../lib/navigation'

/** Route guard (docs/04 §4): reads ['me']; without a session, redirects to /login?next=. */
export function RequireAuth() {
  const me = useMe()
  const location = useLocation()

  if (me.isPending) {
    return (
      <div role="status" className="flex min-h-screen items-center justify-center gap-2 text-sm text-ink-muted">
        <Spinner /> Checking your session…
      </div>
    )
  }
  if (me.isError) {
    return (
      <main id="main" className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-4">
        <ErrorState error={me.error} onRetry={() => void me.refetch()} />
      </main>
    )
  }
  if (!me.data) {
    return <Navigate to={loginPath(location.pathname + location.search, isSessionEnded())} replace />
  }
  return <Outlet />
}
