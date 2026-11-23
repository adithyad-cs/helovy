import type { ReactNode } from 'react'

/**
 * The page title (`h1`) and its primary action (docs/08 §2). The heading takes focus on
 * route changes (tabIndex -1; docs/08 §8).
 */
export function PageHeader({
  title,
  description,
  actions,
  eyebrow,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  eyebrow?: ReactNode
}) {
  return (
    <header className="mb-6 flex flex-col gap-4 md:mb-8 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        {eyebrow ? <div className="mb-2 text-sm text-ink-muted">{eyebrow}</div> : null}
        <h1
          tabIndex={-1}
          className="font-serif text-2xl leading-[30px] font-semibold text-ink outline-none md:text-[30px] md:leading-9"
        >
          {title}
        </h1>
        {description ? <p className="mt-2 max-w-prose text-base text-ink-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  )
}
