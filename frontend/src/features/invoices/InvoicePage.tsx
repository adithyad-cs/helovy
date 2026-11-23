import { useEffect, useState } from 'react'
import { useParams } from 'react-router'

import { useDocument } from '../../api/documents'
import { ApiError } from '../../api/http'
import { PageHeader } from '../../components/ui/PageHeader'
import { DelayedSkeleton, Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/ui/States'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { DraftEditor } from './DraftEditor'
import { FinaliseButton } from './FinaliseButton'
import { InvoiceDetails } from './InvoiceDetails'
import { PreviewButton } from './PreviewDialog'

/** /app/invoices/:documentId: the editor for a draft (docs/08 §15). */
export function InvoicePage() {
  const { documentId = '' } = useParams()
  const [startedAt] = useState(() => Date.now())
  const [pollWindowOpen, setPollWindowOpen] = useState(true)
  useEffect(() => {
    const timer = window.setTimeout(() => setPollWindowOpen(false), 60_000)
    return () => window.clearTimeout(timer)
  }, [])
  // While the final PDF is pending, poll every 1.5 s for up to 60 s (docs/04 §4; docs/08 §19).
  const document = useDocument(documentId, {
    refetchInterval: (data) => (data?.data.pdf?.status === 'pending' && Date.now() - startedAt < 60_000 ? 1500 : false),
  })
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
  const id = document.data.data.id
  if (document.data.data.status === 'finalized') {
    const pending = document.data.data.pdf?.status === 'pending'
    return <InvoiceDetails current={document.data} polling={pending && pollWindowOpen} />
  }
  return (
    <DraftEditor
      key={id}
      current={document.data}
      onReload={() => void document.refetch()}
      actions={{
        render: ({ dirty, saving, live, save, conflict }) => (
          <>
            <PreviewButton documentId={id} disabled={saving || live.lines.length === 0} beforeOpen={save} />
            <FinaliseButton
              current={document.data}
              grandTotal={live.totals?.grand_total ?? null}
              enabled={
                !dirty && !saving && !live.calculating && !live.error && live.lines.length > 0 &&
                Boolean(live.totals) && live.totals?.grand_total !== '0.00'
              }
              onConflict={conflict}
              onReload={() => void document.refetch()}
            />
          </>
        ),
      }}
    />
  )
}
