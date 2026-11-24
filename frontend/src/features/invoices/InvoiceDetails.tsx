import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'

import type { Versioned } from '../../api/businesses'
import { downloadPdf, retryPdf, type AddressSnapshot, type InvoiceDocument } from '../../api/documents'
import { ApiError } from '../../api/http'
import { queryKeys } from '../../api/queryKeys'
import { Banner } from '../../components/ui/Banner'
import { Button } from '../../components/ui/Button'
import { CopyIcon, DownloadIcon, LockIcon } from '../../components/ui/icons'
import { Spinner } from '../../components/ui/Spinner'
import { StatusPill } from '../../components/ui/StatusPill'
import { useToast } from '../../components/ui/Toast'
import { formatDate } from '../../lib/dates'
import { errorMessage } from '../../lib/errors'
import { formatDeduction, formatMoney, formatPercent, formatQuantity } from '../../lib/money'

const FAILURE_REASON: Record<string, string> = {
  storage_error: 'storage unavailable',
  render_timeout: 'took too long',
  render_error: 'internal error',
  snapshot_integrity: 'internal error',
}

function sizeLabel(bytes: number | null): string {
  if (!bytes) return '—'
  return bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function AddressBlock({ title, name, lines, contact }: { title: string; name: string; lines: AddressSnapshot; contact: Array<string | null> }) {
  const cityLine = [lines.city, lines.postal_code].filter(Boolean).join(' ')
  return (
    <div>
      <p className="text-xs font-semibold tracking-wide text-ink-muted uppercase">{title}</p>
      <p className="mt-1 font-semibold text-ink">{name}</p>
      <div className="text-sm text-ink">
        {[lines.line1, lines.line2, cityLine || null, lines.state_name ? `${lines.state_name}, India` : null, ...contact]
          .filter(Boolean)
          .map((line) => (
            <p key={line}>{line}</p>
          ))}
      </div>
    </div>
  )
}

/** The finalised invoice, read-only, entirely from the snapshot (docs/08 §19). */
export function InvoiceDetails({ current, polling }: { current: Versioned<InvoiceDocument>; polling: boolean }) {
  const document = current.data
  const pdf = document.pdf
  const queryClient = useQueryClient()
  const toast = useToast()
  const [downloadProblem, setDownloadProblem] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const previousStatus = useRef(pdf?.status)
  const [announcement, setAnnouncement] = useState('')
  const headingRef = useRef<HTMLHeadingElement>(null)

  // After finalising, the dialog and its trigger are gone: keep keyboard focus on the page
  // by moving it to the invoice number (docs/08 §8).
  useEffect(() => {
    if (window.document.activeElement === window.document.body) headingRef.current?.focus()
  }, [])

  useEffect(() => {
    if (previousStatus.current !== pdf?.status) {
      previousStatus.current = pdf?.status
      const message = pdf?.status === 'ready' ? 'PDF ready' : pdf?.status === 'failed' ? 'PDF generation failed' : ''
      const timer = window.setTimeout(() => setAnnouncement(message), 0)
      return () => window.clearTimeout(timer)
    }
  }, [pdf?.status])

  const download = useMutation({
    mutationFn: () => downloadPdf(document.id),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = `${(document.number ?? 'invoice').replace(/\//g, '-')}.pdf`
      window.document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      setDownloadProblem(null)
      toast.success('PDF downloaded.')
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === 'pdf_not_ready') {
        void queryClient.invalidateQueries({ queryKey: queryKeys.document(document.id) })
      }
      setDownloadProblem(errorMessage(error))
    },
  })

  const retry = useMutation({
    mutationFn: () => retryPdf(document.id),
    onSettled: () => void queryClient.invalidateQueries({ queryKey: queryKeys.document(document.id) }),
    onError: (error) => toast.error(error instanceof ApiError && error.code === 'rate_limited' ? 'Please wait a moment and try again.' : errorMessage(error)),
  })

  async function copyHash(value: string) {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      toast.error('Copying is not available in this browser.')
    }
  }

  const slow = pdf?.status === 'pending' && pdf.retry_available
  const seller = document.seller
  const buyer = document.buyer

  return (
    <article>
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
      <nav aria-label="Breadcrumb" className="mb-2 text-sm text-ink-muted">
        <Link to="/app/invoices" className="hover:text-ink hover:underline">
          Invoices
        </Link>{' '}
        / {document.number}
      </nav>
      <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 ref={headingRef} tabIndex={-1} className="font-serif text-[30px] leading-9 font-semibold text-ink tabular-nums outline-none md:text-[34px] md:leading-10">
              {document.number}
            </h1>
            <StatusPill tone="finalised">Finalised</StatusPill>
          </div>
          <p className="mt-2 flex items-center gap-1.5 text-sm text-ink-muted">
            <LockIcon width={16} height={16} /> Finalised invoices can&apos;t be edited.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => download.mutate()} disabled={pdf?.status !== 'ready'} loading={download.isPending} loadingText="Downloading…">
            <DownloadIcon width={18} height={18} /> Download PDF
          </Button>
          {pdf?.retry_available ? (
            <Button variant="secondary" onClick={() => retry.mutate()} loading={retry.isPending} loadingText="Retrying…">
              Retry PDF
            </Button>
          ) : null}
        </div>
      </header>

      <Banner tone="warning" className="mt-6">
        Specimen — demonstration document, not a tax invoice.
      </Banner>
      {downloadProblem ? (
        <Banner tone="danger" className="mt-3">
          {downloadProblem}
        </Banner>
      ) : null}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_18.75rem] lg:items-start">
        <div className="flex min-w-0 flex-col gap-6">
          <section className="rounded-card border border-line bg-surface p-4 md:p-6" aria-label="Invoice details">
            <dl className="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
              <div>
                <dt className="text-ink-muted">Issue date</dt>
                <dd className="font-medium text-ink">{formatDate(document.issue_date)}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Due date</dt>
                <dd className="font-medium text-ink">{formatDate(document.due_date)}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Customer</dt>
                <dd className="font-medium text-ink">{document.customer.display_name}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">Reference</dt>
                <dd className="font-medium text-ink">{document.reference ?? '—'}</dd>
              </div>
            </dl>
            {seller && buyer ? (
              <div className="mt-6 grid grid-cols-1 gap-6 border-t border-line pt-6 md:grid-cols-2">
                <AddressBlock title="From" name={seller.legal_name} lines={seller.address} contact={[seller.phone, seller.email, seller.gstin ? `GSTIN: ${seller.gstin}` : null]} />
                <AddressBlock title="Bill to" name={buyer.display_name} lines={buyer.address} contact={[buyer.contact_name, buyer.email, buyer.phone, buyer.gstin ? `GSTIN: ${buyer.gstin}` : null]} />
              </div>
            ) : null}
          </section>

          <section className="overflow-hidden rounded-card border border-line bg-surface" aria-labelledby="issued-lines">
            <h2 id="issued-lines" className="px-4 pt-4 text-xl leading-7 font-semibold text-ink md:px-6">
              Line items
            </h2>
            <div className="overflow-x-auto">
              <table className="mt-3 w-full min-w-[40rem] border-collapse text-left text-sm">
                <thead className="bg-paper text-xs tracking-wide text-ink-muted uppercase">
                  <tr>
                    <th scope="col" className="px-4 py-2 font-medium md:pl-6">#</th>
                    <th scope="col" className="px-2 py-2 font-medium">Description</th>
                    <th scope="col" className="px-2 py-2 text-right font-medium">Qty</th>
                    <th scope="col" className="px-2 py-2 font-medium">Unit</th>
                    <th scope="col" className="px-2 py-2 text-right font-medium">Unit price</th>
                    <th scope="col" className="px-2 py-2 text-right font-medium">Discount</th>
                    <th scope="col" className="px-4 py-2 text-right font-medium md:pr-6">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {document.lines.map((line) => (
                    <tr key={line.position} className="border-t border-line align-top">
                      <td className="px-4 py-3 text-ink-muted md:pl-6">{line.position}</td>
                      <td className="px-2 py-3 whitespace-pre-line text-ink">{line.description}</td>
                      <td className="px-2 py-3 text-right text-ink tabular-nums">{formatQuantity(line.quantity)}</td>
                      <td className="px-2 py-3 text-ink">{line.unit ?? ''}</td>
                      <td className="px-2 py-3 text-right text-ink tabular-nums">{formatMoney(line.unit_price)}</td>
                      <td className="px-2 py-3 text-right text-ink tabular-nums">
                        {line.discount_type === 'percent' && line.discount_value
                          ? `${formatPercent(line.discount_value)} (${formatMoney(line.discount)})`
                          : line.discount_type === 'amount'
                            ? formatMoney(line.discount)
                            : '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-ink tabular-nums md:pr-6">{formatMoney(line.line_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {document.notes || document.terms ? (
            <section className="grid grid-cols-1 gap-4 rounded-card border border-line bg-surface p-4 md:grid-cols-2 md:p-6">
              {document.notes ? (
                <div>
                  <h2 className="text-sm font-semibold text-ink-muted">Notes</h2>
                  <p className="mt-1 text-sm whitespace-pre-line text-ink">{document.notes}</p>
                </div>
              ) : null}
              {document.terms ? (
                <div>
                  <h2 className="text-sm font-semibold text-ink-muted">Terms</h2>
                  <p className="mt-1 text-sm whitespace-pre-line text-ink">{document.terms}</p>
                </div>
              ) : null}
            </section>
          ) : null}

          <details className="group rounded-card border border-line bg-surface p-4 md:p-6">
            <summary className="cursor-pointer text-base font-semibold text-ink">Integrity</summary>
            <p className="mt-2 text-sm text-ink-muted">
              These fingerprints show that the invoice and its PDF have not changed since they were issued.
            </p>
            <dl className="mt-3 flex flex-col gap-3 text-sm">
              <div>
                <dt className="text-ink-muted">Snapshot SHA-256</dt>
                <dd className="font-mono text-xs break-all text-ink">{document.snapshot_sha256}</dd>
              </div>
              <div>
                <dt className="text-ink-muted">PDF SHA-256</dt>
                <dd className="font-mono text-xs break-all text-ink">{pdf?.sha256 ?? 'Not available until the PDF is ready'}</dd>
              </div>
            </dl>
          </details>
        </div>

        <aside className="flex flex-col gap-6 lg:sticky lg:top-20" aria-label="Totals and PDF">
          <section className="rounded-card border border-line bg-surface p-4 md:p-6">
            <h2 className="text-xl leading-7 font-semibold text-ink">Totals</h2>
            <dl className="mt-4 flex flex-col gap-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-ink-muted">Subtotal</dt>
                <dd className="font-medium text-ink tabular-nums">{formatMoney(document.totals.gross_total)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-muted">Discount</dt>
                <dd className="font-medium text-ink tabular-nums">{formatDeduction(document.totals.discount_total)}</dd>
              </div>
              <div className="mt-2 flex items-baseline justify-between border-t border-line pt-3">
                <dt className="text-base font-semibold text-ink">Total</dt>
                <dd className="text-2xl font-semibold text-ink tabular-nums">{formatMoney(document.totals.grand_total)}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-card border border-line bg-surface p-4 md:p-6" aria-labelledby="pdf-heading">
            <div className="flex items-center justify-between">
              <h2 id="pdf-heading" className="text-xl leading-7 font-semibold text-ink">
                PDF
              </h2>
              {pdf ? (
                <StatusPill tone={pdf.status === 'ready' ? 'ready' : pdf.status === 'failed' ? 'failed' : 'pending'}>
                  {pdf.status === 'ready' ? 'Ready' : pdf.status === 'failed' ? 'Failed' : 'Pending'}
                </StatusPill>
              ) : null}
            </div>
            {pdf?.status === 'ready' ? (
              <div className="mt-3 text-sm">
                <p className="font-medium text-accent">PDF ready</p>
                <p className="mt-1 text-ink-muted">{sizeLabel(pdf.size_bytes)}</p>
                <div className="mt-2 flex items-center gap-2">
                  <code className="rounded bg-paper px-2 py-1 font-mono text-xs text-ink">{pdf.sha256?.slice(0, 16)}…</code>
                  <button
                    type="button"
                    onClick={() => pdf.sha256 && void copyHash(pdf.sha256)}
                    className="flex h-8 items-center gap-1 rounded-control px-2 text-xs font-medium text-ink-muted hover:bg-tint-neutral hover:text-ink"
                    aria-label="Copy the full PDF SHA-256"
                  >
                    <CopyIcon width={14} height={14} /> {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>
            ) : pdf?.status === 'failed' ? (
              <div className="mt-3 text-sm">
                <p className="font-medium text-danger">PDF generation failed</p>
                <p className="mt-1 text-ink-muted">Reason: {FAILURE_REASON[pdf.last_error_code ?? ''] ?? 'internal error'}.</p>
                <p className="mt-1 text-ink-muted">The invoice number is kept; Retry renders the same issued content again.</p>
              </div>
            ) : (
              <div className="mt-3 text-sm">
                <p className="flex items-center gap-2 font-medium text-warning">
                  <Spinner /> Generating PDF…
                </p>
                {slow ? <p className="mt-1 text-ink-muted">This is taking longer than expected.</p> : null}
                {!polling && !slow ? <p className="mt-1 text-ink-muted">Refresh the page to check again.</p> : null}
              </div>
            )}
          </section>
        </aside>
      </div>
    </article>
  )
}
