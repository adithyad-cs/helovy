import type { ReactNode } from 'react'

import { Banner } from './Banner'

export function FormSection({ title, description, children }: { title: string; description?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-card border border-line bg-surface p-4 md:p-6">
      <h2 className="text-xl leading-7 font-semibold text-ink">{title}</h2>
      {description ? <p className="mt-1 text-sm text-ink-muted">{description}</p> : null}
      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
    </section>
  )
}

export interface SummaryItem {
  field: string
  label: string
  message: string
}

/** After a failed submit: a summary at the top, each item moving focus to its field (docs/08 §8). */
export function ErrorSummary({ items, extra, onFocus }: { items: SummaryItem[]; extra?: string[]; onFocus: (field: string) => void }) {
  if (!items.length && !extra?.length) return null
  return (
    <Banner tone="danger" title="Please correct the highlighted fields.">
      <ul className="mt-1 list-disc pl-5">
        {items.map((item) => (
          <li key={item.field}>
            <button type="button" className="text-left underline underline-offset-2" onClick={() => onFocus(item.field)}>
              {item.label}: {item.message}
            </button>
          </li>
        ))}
        {extra?.map((message) => <li key={message}>{message}</li>)}
      </ul>
    </Banner>
  )
}
