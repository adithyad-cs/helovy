import type { ReactNode } from 'react'

import { errorMessage, requestIdOf } from '../../lib/errors'
import { Button } from './Button'

/** One sentence explaining why it is empty, and the next action (docs/08 §9). */
export function EmptyState({ icon, title, children, action }: { icon?: ReactNode; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-card border border-dashed border-line bg-surface px-6 py-12 text-center">
      {icon ? <div className="text-ink-muted">{icon}</div> : null}
      <p className="text-base font-medium text-ink">{title}</p>
      {children ? <div className="max-w-md text-sm text-ink-muted">{children}</div> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  )
}

/** Plain message, request ID in small text, and Retry (docs/08 §9). */
export function ErrorState({ error, onRetry, title }: { error: unknown; onRetry?: () => void; title?: string }) {
  const requestId = requestIdOf(error)
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-card border border-danger/30 bg-tint-danger px-6 py-10 text-center">
      <p className="text-base font-medium text-ink">{title ?? errorMessage(error)}</p>
      {title ? <p className="text-sm text-ink">{errorMessage(error)}</p> : null}
      {requestId ? <p className="text-xs text-ink-muted">Reference: {requestId}</p> : null}
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  )
}
