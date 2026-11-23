import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'

import { useCustomerList } from '../../api/customers'
import { useBusinessId } from '../../app/RequireBusiness'
import { Button, ButtonLink } from '../../components/ui/Button'
import { controlClasses } from '../../components/ui/Field'
import { PlusIcon, SearchIcon, UsersIcon } from '../../components/ui/icons'
import { PageHeader } from '../../components/ui/PageHeader'
import { DelayedSkeleton, SkeletonRows } from '../../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../../components/ui/States'
import { formatTimestampDate } from '../../lib/dates'
import { useDocumentTitle } from '../../lib/useDocumentTitle'

/** /app/customers (docs/08 §14.1): newest first, prefix search, "Load more". */
export function CustomerListPage() {
  useDocumentTitle('Customers')
  const businessId = useBusinessId()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const q = (params.get('q') ?? '').trim()
  const [search, setSearch] = useState(q)
  const list = useCustomerList(businessId, q)

  // Debounced 300 ms; the search lives in the URL (?q=).
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = search.trim()
      if (next !== q) setParams(next ? { q: next } : {}, { replace: true })
    }, 300)
    return () => window.clearTimeout(timer)
  }, [search, q, setParams])

  const items = list.data?.pages.flatMap((page) => page.items) ?? []

  return (
    <>
      <PageHeader
        title="Customers"
        actions={
          <ButtonLink to="/app/customers/new">
            <PlusIcon width={18} height={18} /> New customer
          </ButtonLink>
        }
      />
      <div className="mb-4 max-w-md">
        <label htmlFor="customer-search" className="mb-1.5 block text-sm font-medium text-ink">
          Search by name
        </label>
        <div className="relative">
          <SearchIcon width={18} height={18} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-muted" />
          <input
            id="customer-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Start of the customer name"
            maxLength={100}
            autoComplete="off"
            className={controlClasses(false, 'min-h-11 py-2 pl-10')}
          />
        </div>
      </div>

      {list.isPending ? (
        <DelayedSkeleton label="Loading customers…">
          <SkeletonRows rows={5} />
        </DelayedSkeleton>
      ) : list.isError ? (
        <ErrorState error={list.error} onRetry={() => void list.refetch()} />
      ) : items.length === 0 ? (
        q ? (
          <EmptyState icon={<SearchIcon width={28} height={28} />} title={`No customers start with “${q}”.`}>
            <Button variant="secondary" onClick={() => setSearch('')}>
              Clear search
            </Button>
          </EmptyState>
        ) : (
          <EmptyState
            icon={<UsersIcon width={28} height={28} />}
            title="No customers yet."
            action={
              <ButtonLink to="/app/customers/new">
                <PlusIcon width={18} height={18} /> New customer
              </ButtonLink>
            }
          >
            Add your first customer to start invoicing.
          </EmptyState>
        )
      ) : (
        <>
          <div className="hidden overflow-hidden rounded-card border border-line bg-surface md:block">
            <table className="w-full border-collapse text-left text-sm">
              <thead className="bg-paper text-xs tracking-wide text-ink-muted uppercase">
                <tr>
                  <th scope="col" className="px-4 py-3 font-medium">Name</th>
                  <th scope="col" className="px-4 py-3 font-medium">Contact</th>
                  <th scope="col" className="px-4 py-3 font-medium">Email</th>
                  <th scope="col" className="px-4 py-3 font-medium">City</th>
                  <th scope="col" className="px-4 py-3 font-medium">Added</th>
                </tr>
              </thead>
              <tbody>
                {items.map((customer) => (
                  <tr
                    key={customer.id}
                    onClick={() => navigate(`/app/customers/${customer.id}`)}
                    className="cursor-pointer border-t border-line transition-colors duration-150 hover:bg-paper"
                  >
                    <td className="px-4 py-3 font-medium text-ink">
                      <Link to={`/app/customers/${customer.id}`} className="rounded-control hover:underline" onClick={(e) => e.stopPropagation()}>
                        {customer.display_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-ink-muted">{customer.contact_name ?? '—'}</td>
                    <td className="max-w-[240px] truncate px-4 py-3 text-ink-muted">{customer.email ?? '—'}</td>
                    <td className="px-4 py-3 text-ink-muted">{customer.city ?? '—'}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-ink-muted">{formatTimestampDate(customer.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ul className="flex flex-col gap-3 md:hidden">
            {items.map((customer) => (
              <li key={customer.id}>
                <Link
                  to={`/app/customers/${customer.id}`}
                  className="block rounded-card border border-line bg-surface p-4 transition-colors hover:bg-paper"
                >
                  <p className="font-medium text-ink">{customer.display_name}</p>
                  <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                    <dt className="text-ink-muted">Contact</dt>
                    <dd className="truncate text-ink">{customer.contact_name ?? '—'}</dd>
                    <dt className="text-ink-muted">Email</dt>
                    <dd className="truncate text-ink">{customer.email ?? '—'}</dd>
                    <dt className="text-ink-muted">City</dt>
                    <dd className="text-ink">{customer.city ?? '—'}</dd>
                    <dt className="text-ink-muted">Added</dt>
                    <dd className="text-ink">{formatTimestampDate(customer.created_at)}</dd>
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
