import { Link, useNavigate } from 'react-router'

import { useMe } from '../../api/auth'
import { useDocumentList } from '../../api/documents'
import { ButtonLink } from '../../components/ui/Button'
import { BuildingIcon, DocumentIcon, PlusIcon } from '../../components/ui/icons'
import { PageHeader } from '../../components/ui/PageHeader'
import { DelayedSkeleton, SkeletonRows } from '../../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../../components/ui/States'
import { formatDate } from '../../lib/dates'
import { formatMoney } from '../../lib/money'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { DocumentStatusPill } from '../invoices/DocumentStatus'

/** /app (docs/08 §12.3): set-up card, or quick actions and the five most recent invoices.
 *  No charts, revenue figures or analytics (docs/03 §8). */
export function DashboardPage() {
  const me = useMe()
  useDocumentTitle('Dashboard')
  const business = me.data?.business

  if (!business) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <section className="card-enter flex flex-col items-start gap-4 rounded-card border border-line bg-surface p-6 md:flex-row md:items-center md:p-8">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-tint-accent text-accent">
            <BuildingIcon />
          </span>
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-ink">Set up your business</h2>
            <p className="mt-1 text-sm text-ink-muted">Your details appear on every invoice.</p>
          </div>
          <ButtonLink to="/app/business" size="lg">
            Set up business
          </ButtonLink>
        </section>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Dashboard"
        description={business.legal_name}
        actions={
          <>
            <ButtonLink to="/app/invoices/new">
              <PlusIcon width={18} height={18} /> New invoice
            </ButtonLink>
            <ButtonLink to="/app/customers/new" variant="secondary">
              <PlusIcon width={18} height={18} /> New customer
            </ButtonLink>
          </>
        }
      />
      <RecentInvoices businessId={business.id} />
    </>
  )
}

function RecentInvoices({ businessId }: { businessId: string }) {
  const recent = useDocumentList(businessId, { limit: 5 })
  const navigate = useNavigate()
  const items = recent.data?.pages[0]?.items ?? []
  return (
    <section className="rounded-card border border-line bg-surface" aria-labelledby="recent-heading">
      <div className="flex items-center justify-between px-4 pt-4 md:px-6 md:pt-5">
        <h2 id="recent-heading" className="text-xl leading-7 font-semibold text-ink">
          Recent invoices
        </h2>
        <Link to="/app/invoices" className="text-sm font-medium text-accent hover:text-accent-hover hover:underline">
          View all invoices
        </Link>
      </div>
      <div className="p-4 md:p-6">
        {recent.isPending ? (
          <DelayedSkeleton label="Loading recent invoices…">
            <SkeletonRows rows={5} />
          </DelayedSkeleton>
        ) : recent.isError ? (
          <ErrorState error={recent.error} onRetry={() => void recent.refetch()} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<DocumentIcon width={28} height={28} />}
            title="No invoices yet. Create your first invoice."
            action={
              <ButtonLink to="/app/invoices/new">
                <PlusIcon width={18} height={18} /> New invoice
              </ButtonLink>
            }
          />
        ) : (
          <ul className="divide-y divide-line">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => navigate(`/app/invoices/${item.id}`)}
                  className="grid w-full grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 rounded-control px-2 py-3 text-left transition-colors hover:bg-paper md:grid-cols-[10rem_1fr_7rem_8rem_6.5rem]"
                >
                  <span className="font-semibold text-ink tabular-nums">{item.number ?? 'Draft'}</span>
                  <span className="justify-self-end md:hidden">
                    <DocumentStatusPill status={item.status} />
                  </span>
                  <span className="truncate text-sm text-ink">{item.customer_name}</span>
                  <span className="hidden text-sm text-ink-muted md:block">{formatDate(item.issue_date)}</span>
                  <span className="text-right text-sm font-medium text-ink tabular-nums">{item.grand_total ? formatMoney(item.grand_total) : '—'}</span>
                  <span className="hidden justify-self-end md:block">
                    <DocumentStatusPill status={item.status} />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
