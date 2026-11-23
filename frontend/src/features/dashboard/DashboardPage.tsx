import { useMe } from '../../api/auth'
import { PageHeader } from '../../components/ui/PageHeader'
import { useDocumentTitle } from '../../lib/useDocumentTitle'

/** /app (docs/08 §12.3). The business set-up card and recent invoices arrive with M2 and M6. */
export function DashboardPage() {
  const me = useMe()
  useDocumentTitle('Dashboard')
  return (
    <>
      <PageHeader title="Dashboard" description={me.data ? `Signed in to ${me.data.organization.name}.` : undefined} />
    </>
  )
}
