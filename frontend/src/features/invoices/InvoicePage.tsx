import { useParams } from 'react-router'

import { useDocument } from '../../api/documents'
import { ApiError } from '../../api/http'
import { PageHeader } from '../../components/ui/PageHeader'
import { DelayedSkeleton, Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/ui/States'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { DraftEditor } from './DraftEditor'

/** /app/invoices/:documentId: the editor for a draft (docs/08 §15). */
export function InvoicePage() {
  const { documentId = '' } = useParams()
  const document = useDocument(documentId)
  useDocumentTitle(document.data?.data.number ?? 'Draft invoice')

  if (document.isPending) {
    return (
      <>
        <PageHeader title="Invoice" />
        <DelayedSkeleton label="Loading the invoice…">
          <div className="grid gap-6 lg:grid-cols-[1fr_18.75rem]">
            <Skeleton className="h-96 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </DelayedSkeleton>
      </>
    )
  }
  if (document.isError) {
    const notFound = document.error instanceof ApiError && document.error.status === 404
    return (
      <>
        <PageHeader title="Invoice" />
        <ErrorState
          error={document.error}
          title={notFound ? "This invoice doesn't exist or you don't have access." : undefined}
          onRetry={notFound ? undefined : () => void document.refetch()}
        />
      </>
    )
  }
  return <DraftEditor key={document.data.data.id} current={document.data} onReload={() => void document.refetch()} />
}
