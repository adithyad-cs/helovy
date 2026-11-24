import type { DocumentListItem } from '../../api/documents'
import { StatusPill } from '../../components/ui/StatusPill'

export function DocumentStatusPill({ status }: { status: DocumentListItem['status'] }) {
  return status === 'finalized' ? <StatusPill tone="finalised">Finalised</StatusPill> : <StatusPill tone="draft">Draft</StatusPill>
}

export function PdfStatusText({ status }: { status: DocumentListItem['pdf_status'] }) {
  if (status === 'ready') return <StatusPill tone="ready">Ready</StatusPill>
  if (status === 'pending') return <StatusPill tone="pending">Pending</StatusPill>
  if (status === 'failed') return <StatusPill tone="failed">Failed</StatusPill>
  return <span className="text-ink-muted">—</span>
}
