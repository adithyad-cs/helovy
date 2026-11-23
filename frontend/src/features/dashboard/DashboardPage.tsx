import { useMe } from '../../api/auth'
import { ButtonLink } from '../../components/ui/Button'
import { BuildingIcon, PlusIcon } from '../../components/ui/icons'
import { PageHeader } from '../../components/ui/PageHeader'
import { useDocumentTitle } from '../../lib/useDocumentTitle'

/** /app (docs/08 §12.3). Recent invoices arrive with the history list (M6). */
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
    </>
  )
}
