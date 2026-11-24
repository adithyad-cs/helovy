import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { useDocumentList } from '../../api/documents'
import { useBusinessId } from '../../app/RequireBusiness'
import { Button, ButtonLink } from '../../components/ui/Button'
import { cx } from '../../components/ui/cx'
import { controlClasses } from '../../components/ui/Field'
import { DocumentIcon, PlusIcon, SearchIcon } from '../../components/ui/icons'
import { PageHeader } from '../../components/ui/PageHeader'
import { DelayedSkeleton, SkeletonRows } from '../../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../../components/ui/States'
import { formatDate } from '../../lib/dates'
import { formatMoney } from '../../lib/money'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { DocumentStatusPill, PdfStatusText } from './DocumentStatus'

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'draft', label: 'Drafts' },
  { value: 'finalized', label: 'Finalised' },
] as const

/** /app/invoices (docs/08 §18): status filter, prefix search, newest first, "Load more". */
export function InvoicesIndexPage() {
  useDocumentTitle('Invoices')
  const businessId = useBusinessId()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const rawStatus = params.get('status')
  const status = rawStatus === 'draft' || rawStatus === 'finalized' ? rawStatus : undefined
  const q = (params.get('q') ?? '').trim()
  const [search, setSearch] = useState(q)
  const list = useDocumentList(businessId, { status, q: q || undefined })

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = search.trim()
      if (next !== q) {
        const updated = new URLSearchParams(params)
        if (next) updated.set('q', next)
        else updated.delete('q')
        setParams(updated, { replace: true })
      }
    }, 300)
    return () => window.clearTimeout(timer)
  }, [search, q, params, setParams])

  function setStatus(value: string) {
    const updated = new URLSearchParams(params)
    if (value) updated.set('status', value)
    else updated.delete('status')
    setParams(updated, { replace: true })
  }

  const items = list.data?.pages.flatMap((page) => page.items) ?? []
  const filtered = Boolean(status || q)

  return (
    <>
      <PageHeader
        title="Invoices"
        actions={
          <ButtonLink to="/app/invoices/new">
            <PlusIcon width={18} height={18} /> New invoice
          </ButtonLink>
        }
      />
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div role="group" aria-label="Filter by status" className="inline-flex w-fit rounded-control border border-field-border bg-surface p-0.5">
          {FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              aria-pressed={(status ?? '') === filter.value}
              onClick={() => setStatus(filter.value)}
              className={cx(
                'min-h-9 rounded-[5px] px-4 text-sm font-medium transition-colors duration-150',
                (status ?? '') === filter.value ? 'bg-ink text-paper' : 'text-ink-muted hover:text-ink',
              )}
            >
              {filter.label}
            </button>
          ))}
        </div>
        <div className="w-full md:max-w-sm">
          <label htmlFor="invoice-search" className="mb-1.5 block text-sm font-medium text-ink">
            Search by number or customer
          </label>
          <div className="relative">
            <SearchIcon width={18} height={18} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-muted" />
            <input
              id="invoice-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="INV/26-27 or customer name"
              maxLength={50}
              autoComplete="off"
              className={controlClasses(false, 'min-h-11 py-2 pl-10')}
            />
          </div>
        </div>
      </div>

      {list.isPending ? (
        <DelayedSkeleton label="Loading invoices…">
          <SkeletonRows rows={6} />
        </DelayedSkeleton>
      ) : list.isError ? (
        <ErrorState error={list.error} onRetry={() => void list.refetch()} />
      ) : items.length === 0 ? (
        filtered ? (
          <EmptyState icon={<SearchIcon width={28} height={28} />} title="No invoices match these filters.">
            <Button
              variant="secondary"
              onClick={() => {
                setSearch('')
                setParams({}, { replace: true })
              }}
            >
              Clear filters
            </Button>
          </EmptyState>
        ) : (
          <EmptyState
            icon={<DocumentIcon width={28} height={28} />}
            title="No invoices yet."
            action={
              <ButtonLink to="/app/invoices/new">
                <PlusIcon width={18} height={18} /> New invoice
              </ButtonLink>
            }
          >
            Create your first invoice; it is saved as a draft until you finalise it.
          </EmptyState>
        )
      ) : (
        <>
          <div className="hidden overflow-hidden rounded-card border border-line bg-surface md:block">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="bg-paper text-xs tracking-wide text-ink-muted uppercase">
                <tr>
                  <th scope="col" className="px-4 py-3 font-medium">Number</th>
                  <th scope="col" className="px-4 py-3 font-medium">Customer</th>
                  <th scope="col" className="px-4 py-3 font-medium">Issue date</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">Total</th>
                  <th scope="col" className="px-4 py-3 font-medium">Status</th>
                  <th scope="col" className="px-4 py-3 font-medium">PDF</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} onClick={() => navigate(`/app/invoices/${item.id}`)} className="cursor-pointer border-t border-line transition-colors duration-150 hover:bg-paper">
                    <td className="px-4 py-3 font-medium whitespace-nowrap text-ink tabular-nums">
                      <Link to={`/app/invoices/${item.id}`} onClick={(e) => e.stopPropagation()} className="rounded-control hover:underline">
                        {item.number ?? 'Draft'}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-ink">{item.customer_name}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-ink-muted">{formatDate(item.issue_date)}</td>
                    <td className="px-4 py-3 text-right font-medium whitespace-nowrap text-ink tabular-nums">{item.grand_total ? formatMoney(item.grand_total) : '—'}</td>
                    <td className="px-4 py-3"><DocumentStatusPill status={item.status} /></td>
                    <td className="px-4 py-3"><PdfStatusText status={item.pdf_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="flex flex-col gap-3 md:hidden">
            {items.map((item) => (
              <li key={item.id}>
                <Link to={`/app/invoices/${item.id}`} className="block rounded-card border border-line bg-surface p-4 transition-colors hover:bg-paper">
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-semibold text-ink tabular-nums">{item.number ?? 'Draft'}</p>
                    <DocumentStatusPill status={item.status} />
                  </div>
                  <p className="mt-1 text-sm text-ink">{item.customer_name}</p>
                  <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                    <dt className="text-ink-muted">Issue date</dt>
                    <dd className="text-ink">{formatDate(item.issue_date)}</dd>
                    <dt className="text-ink-muted">Total</dt>
                    <dd className="text-ink tabular-nums">{item.grand_total ? formatMoney(item.grand_total) : '—'}</dd>
                    <dt className="text-ink-muted">PDF</dt>
                    <dd><PdfStatusText status={item.pdf_status} /></dd>
                  </dl>
                </Link>
              </li>
            ))}
          </ul>
          {list.hasNextPage ? (
            <div className="mt-4 flex justify-center">
              <Button variant="secondary" onClick={() => void list.fetchNextPage()} loading={list.isFetchingNextPage} loadingText="Loading…">
                Load more
              </Button>
            </div>
          ) : null}
        </>
      )}
    </>
  )
}
