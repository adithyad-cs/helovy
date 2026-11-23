import { Navigate, Outlet } from 'react-router'

import { useMe } from '../api/auth'

/** "Business required" routes redirect to the profile with a banner (docs/08 §12.1). */
export function RequireBusiness() {
  const me = useMe()
  if (!me.data?.business) {
    return <Navigate to="/app/business" replace state={{ reason: 'business-required' }} />
  }
  return <Outlet />
}

/** The session's business ID; only call inside <RequireBusiness>. */
export function useBusinessId(): string {
  const me = useMe()
  const id = me.data?.business?.id
  if (!id) throw new Error('useBusinessId needs a business (RequireBusiness)')
  return id
}
