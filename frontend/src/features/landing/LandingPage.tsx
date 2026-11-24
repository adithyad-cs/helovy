import { Link } from 'react-router'

import { useMe } from '../../api/auth'
import { Wordmark } from '../../app/Wordmark'
import { buttonClasses } from '../../components/ui/Button'
import { ArrowRightIcon, CheckIcon, LockIcon, DocumentIcon } from '../../components/ui/icons'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { LedgerAnimation } from './LedgerAnimation'

const VALUE_POINTS = [
  {
    title: 'Totals you can trust',
    body: 'Calculated on the server with exact decimal arithmetic.',
    icon: <CheckIcon />,
  },
  {
    title: 'Numbered once, then locked',
    body: 'Each finalised invoice gets a unique number and can no longer be changed.',
    icon: <LockIcon />,
  },
  {
    title: 'Retrievable as issued',
    body: 'The issued PDF is stored privately, and every download is identical to the original.',
    icon: <DocumentIcon />,
  },
] as const

const WORKFLOW = ['Business', 'Customer', 'Invoice', 'Finalise', 'PDF', 'History'] as const

/**
 * ENTER THE SYSTEM goes to /app when the cached session is valid, otherwise to /login
 * (docs/08 §10.1). /login itself redirects to /app when a session exists, so a pending or
 * failed session check still leads somewhere sensible.
 */
function EnterButton({ size = 'lg', compact = false }: { size?: 'md' | 'lg'; compact?: boolean }) {
  const me = useMe()
  const target = me.data ? '/app' : '/login'
  const spacing = compact ? 'whitespace-nowrap px-3 text-[13px] tracking-[0.04em] md:px-4 md:text-sm md:tracking-[0.08em]' : 'tracking-[0.08em]'
  return (
    <Link to={target} className={buttonClasses('primary', size, spacing)} aria-busy={me.isPending || undefined}>
      ENTER THE SYSTEM
      <ArrowRightIcon width={18} height={18} className={compact ? 'hidden md:block' : undefined} />
    </Link>
  )
}

/** The public landing page `/` (docs/08 §10; docs/03 L-01). */
export function LandingPage() {
  useDocumentTitle('Correct invoices, numbered once')
  return (
    <div className="min-h-screen bg-paper text-ink">
      <a href="#main" className="sr-only z-50 rounded-control bg-surface px-3 py-2 text-sm font-medium focus:not-sr-only focus:fixed focus:top-2 focus:left-2">
        Skip to content
      </a>
      <header className="border-b border-line/70">
        <div className="mx-auto flex h-16 max-w-[1200px] items-center gap-2 px-4 md:gap-3 md:px-6 lg:px-8">
          <span className="md:hidden">
            <Wordmark compact />
          </span>
          <span className="hidden md:inline">
            <Wordmark />
          </span>
          <span className="hidden rounded-full border border-line bg-surface px-2.5 py-0.5 text-xs font-medium text-ink-muted md:inline">
            Demonstration build
          </span>
          <div className="ml-auto">
            <EnterButton size="md" compact />
          </div>
        </div>
      </header>

      <main id="main">
        <section className="mx-auto grid max-w-[1200px] grid-cols-1 items-center gap-12 px-4 pt-12 pb-16 md:px-6 md:pt-16 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)] lg:gap-16 lg:px-8 lg:pt-20 lg:pb-24">
          <div className="card-enter">
            <span className="inline-flex rounded-full border border-line bg-surface px-2.5 py-0.5 text-xs font-medium text-ink-muted md:hidden">
              Demonstration build
            </span>
            <h1 className="mt-4 font-serif text-[34px] leading-10 font-semibold text-ink md:mt-0 md:text-[48px] md:leading-[56px]">
              Correct invoices. Numbered once. Stored exactly as issued.
            </h1>
            <p className="mt-5 max-w-[34rem] text-lg leading-7 text-ink-muted">
              Enter your business details once, add line items, and HIVE DOCS calculates every amount on the server, issues a
              unique invoice number and stores the exact PDF you sent.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-4">
              <EnterButton />
              <a href="#how-it-works" className="text-base font-medium text-accent underline-offset-4 hover:text-accent-hover hover:underline">
                How it works
              </a>
            </div>
          </div>
          <div className="lg:pl-4">
            <LedgerAnimation />
          </div>
        </section>

        <section aria-labelledby="value-heading" className="border-t border-line/70 bg-surface/60">
          <div className="mx-auto max-w-[1200px] px-4 py-14 md:px-6 lg:px-8">
            <h2 id="value-heading" className="sr-only">
              Why HIVE DOCS
            </h2>
            <ul className="grid grid-cols-1 gap-4 md:grid-cols-3 md:gap-6">
              {VALUE_POINTS.map((point) => (
                <li key={point.title} className="rounded-card border border-line bg-surface p-6">
                  <span className="flex h-10 w-10 items-center justify-center rounded-full bg-tint-accent text-accent" aria-hidden="true">
                    {point.icon}
                  </span>
                  <h3 className="mt-4 text-lg font-semibold text-ink">{point.title}</h3>
                  <p className="mt-1.5 text-base text-ink-muted">{point.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="how-it-works" aria-labelledby="workflow-heading" className="scroll-mt-6 border-t border-line/70">
          <div className="mx-auto max-w-[1200px] px-4 py-14 md:px-6 lg:px-8">
            <h2 id="workflow-heading" className="font-serif text-2xl font-semibold text-ink md:text-[30px] md:leading-9">
              How it works
            </h2>
            <ol className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
              {WORKFLOW.map((step, index) => (
                <li key={step} className="relative rounded-card border border-line bg-surface px-4 py-4">
                  <span className="text-xs font-semibold text-ink-muted tabular-nums">{String(index + 1).padStart(2, '0')}</span>
                  <p className="mt-1 text-base font-semibold text-ink">{step}</p>
                  {index < WORKFLOW.length - 1 ? (
                    <span aria-hidden="true" className="absolute top-1/2 -right-2.5 hidden h-px w-2 bg-ink-muted/50 lg:block" />
                  ) : null}
                </li>
              ))}
            </ol>
            <div className="mt-10">
              <EnterButton />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <p className="mx-auto max-w-[1200px] px-4 py-6 text-sm text-ink-muted md:px-6 lg:px-8">
          Demonstration build · PDFs are specimens, not tax invoices · Built by Group 6 for HIVE Hub / Heloavy
        </p>
      </footer>
    </div>
  )
}
