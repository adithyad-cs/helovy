import { cx } from './cx'

type Tone = 'draft' | 'finalised' | 'pending' | 'ready' | 'failed'

const TONES: Record<Tone, string> = {
  draft: 'bg-tint-neutral text-ink-muted',
  finalised: 'bg-tint-accent text-accent',
  pending: 'bg-tint-warning text-warning',
  ready: 'bg-tint-accent text-accent',
  failed: 'bg-tint-danger text-danger',
}

/** Status in words, never colour alone (docs/08 §1, §8). */
export function StatusPill({ tone, children }: { tone: Tone; children: string }) {
  return (
    <span className={cx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold', TONES[tone])}>
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-current" />
      {children}
    </span>
  )
}
