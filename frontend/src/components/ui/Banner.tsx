import type { ReactNode } from 'react'

import { cx } from './cx'

type Tone = 'info' | 'success' | 'warning' | 'danger'

const TONES: Record<Tone, string> = {
  info: 'border-line bg-tint-neutral text-ink',
  success: 'border-accent/30 bg-tint-accent text-ink',
  warning: 'border-warning/30 bg-tint-warning text-ink',
  danger: 'border-danger/30 bg-tint-danger text-ink',
}

const MARKS: Record<Tone, string> = { info: 'i', success: '✓', warning: '!', danger: '!' }
const MARK_TONES: Record<Tone, string> = {
  info: 'bg-ink-muted',
  success: 'bg-accent',
  warning: 'bg-warning',
  danger: 'bg-danger',
}

/** A notice; errors use role="alert", everything else role="status". */
export function Banner({
  tone = 'info',
  title,
  children,
  action,
  className,
}: {
  tone?: Tone
  title?: ReactNode
  children?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={cx('flex items-start gap-3 rounded-card border px-4 py-3 text-sm', TONES[tone], className)}
    >
      <span
        aria-hidden="true"
        className={cx(
          'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white',
          MARK_TONES[tone],
        )}
      >
        {MARKS[tone]}
      </span>
      <div className="min-w-0 flex-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        {children ? <div className={cx(title ? 'mt-0.5' : undefined, 'text-ink')}>{children}</div> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}
