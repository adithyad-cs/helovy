import { useCallback, useEffect, useRef } from 'react'
import { useBlocker } from 'react-router'

/**
 * Unsaved changes: a route blocker and a `beforeunload` prompt while a form is dirty
 * (docs/08 §9). `allowNextNavigation()` lets a successful save navigate away at once.
 */
export function useUnsavedChangesGuard(dirty: boolean) {
  const bypass = useRef(false)
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      !bypass.current && dirty && currentLocation.pathname !== nextLocation.pathname,
  )
  useEffect(() => {
    if (!dirty) return
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault()
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])
  const allowNextNavigation = useCallback(() => {
    bypass.current = true
  }, [])
  return { blocker, allowNextNavigation }
}
