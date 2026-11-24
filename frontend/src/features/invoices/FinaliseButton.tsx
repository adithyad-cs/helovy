import { useQueryClient } from '@tanstack/react-query'
import { AlertDialog } from 'radix-ui'
import { useState } from 'react'

import type { Versioned } from '../../api/businesses'
import { finalizeDocument, type InvoiceDocument } from '../../api/documents'
import { ApiError, NetworkError } from '../../api/http'
import { queryKeys } from '../../api/queryKeys'
import { useBusinessId } from '../../app/RequireBusiness'
import { Banner } from '../../components/ui/Banner'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { errorMessage } from '../../lib/errors'
import { newIdempotencyKey, wait } from '../../lib/idempotency'
import { formatMoney } from '../../lib/money'

const REASONS: Record<string, string> = {
  no_lines: 'add at least one line',
  zero_total: 'the total must be more than ₹0.00',
  total_too_large: 'the total is above the allowed maximum',
  due_date_before_issue_date: 'the due date is before today',
  inactive: 'the selected template is no longer available',
}

const MAX_RETRIES = 3

/**
 * Finalise (docs/08 §15.3): one Idempotency-Key per confirmation; 409 idempotency_in_progress
 * or a network failure retries automatically with the same key after 2 s, up to 3 times.
 */
export function FinaliseButton({
  current,
  enabled,
  grandTotal,
  onConflict,
  onReload,
}: {
  current: Versioned<InvoiceDocument>
  enabled: boolean
  grandTotal: string | null
  onConflict: () => void
  onReload: () => void
}) {
  const businessId = useBusinessId()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [phase, setPhase] = useState<'idle' | 'submitting' | 'confirming'>('idle')
  const [problem, setProblem] = useState<string | null>(null)
  const document = current.data

  async function confirm() {
    const key = newIdempotencyKey()
    setProblem(null)
    setPhase('submitting')
    for (let attempt = 0; attempt <= MAX_RETRIES; attempt += 1) {
      try {
        const issued = await finalizeDocument(document.id, current.etag, key)
        queryClient.setQueryData(queryKeys.document(document.id), issued)
        void queryClient.invalidateQueries({ queryKey: queryKeys.documentsAll(businessId) })
        toast.success(`Invoice ${issued.data.number} finalised.`)
        setOpen(false)
        setPhase('idle')
        return
      } catch (error) {
        const retryable =
          error instanceof NetworkError || (error instanceof ApiError && error.code === 'idempotency_in_progress')
        if (retryable && attempt < MAX_RETRIES) {
          setPhase('confirming')
          await wait(2000)
          continue
        }
        setPhase('idle')
        if (error instanceof ApiError && error.code === 'finalization_blocked') {
          const reasons = error.fieldErrors.map((e) => REASONS[e.code] ?? e.message)
          setProblem(`This invoice can't be finalised yet: ${reasons.join('; ')}.`)
        } else if (error instanceof ApiError && error.code === 'version_mismatch') {
          setOpen(false)
          onConflict()
        } else if (error instanceof ApiError && error.code === 'document_not_draft') {
          setOpen(false)
          toast.error(errorMessage(error))
          onReload()
        } else {
          setProblem(errorMessage(error))
        }
        return
      }
    }
  }

  const busy = phase !== 'idle'
  return (
    <AlertDialog.Root
      open={open}
      onOpenChange={(next) => {
        if (busy) return
        setOpen(next)
        if (next) setProblem(null)
      }}
    >
      <AlertDialog.Trigger asChild>
        <Button className="w-full" disabled={!enabled}>
          Finalise
        </Button>
      </AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="overlay-enter fixed inset-0 z-40 bg-ink/40" />
        <AlertDialog.Content className="dialog-enter fixed top-1/2 left-1/2 z-50 w-[calc(100vw-32px)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-card bg-surface p-6 shadow-[0_16px_48px_rgba(27,42,65,0.22)] outline-none">
          <AlertDialog.Title className="font-serif text-xl font-semibold text-ink">Finalise invoice?</AlertDialog.Title>
          <AlertDialog.Description className="mt-3 text-sm text-ink">
            This assigns the next invoice number and today&apos;s date (India time). After finalising, the invoice can&apos;t be
            edited or deleted. The PDF is marked SPECIMEN — not a tax invoice.
          </AlertDialog.Description>
          <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded-control bg-paper px-4 py-3 text-sm">
            <dt className="text-ink-muted">Customer</dt>
            <dd className="font-medium text-ink">{document.customer.display_name}</dd>
            <dt className="text-ink-muted">Total</dt>
            <dd className="font-semibold text-ink tabular-nums">{formatMoney(grandTotal)}</dd>
          </dl>
          {problem ? (
            <Banner tone="danger" className="mt-4">
              {problem}
            </Banner>
          ) : null}
          {phase === 'confirming' ? (
            <p role="status" className="mt-4 text-sm text-ink-muted">
              Confirming…
            </p>
          ) : null}
          <div className="mt-6 flex flex-col-reverse gap-2 md:flex-row md:justify-end">
            <AlertDialog.Cancel asChild>
              <Button variant="secondary" disabled={busy}>
                Cancel
              </Button>
            </AlertDialog.Cancel>
            <Button onClick={() => void confirm()} loading={busy} loadingText={phase === 'confirming' ? 'Confirming…' : 'Finalising…'}>
              Finalise invoice
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}
