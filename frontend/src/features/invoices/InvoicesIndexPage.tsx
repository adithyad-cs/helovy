import { ButtonLink } from '../../components/ui/Button'
import { PlusIcon } from '../../components/ui/icons'
import { PageHeader } from '../../components/ui/PageHeader'
import { useDocumentTitle } from '../../lib/useDocumentTitle'

/** /app/invoices: the history list arrives in M6; until then this page only starts a new invoice. */
export function InvoicesIndexPage() {
  useDocumentTitle('Invoices')
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
      <p className="max-w-prose text-base text-ink-muted">The invoice history is not available in this build yet.</p>
    </>
  )
}
