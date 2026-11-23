import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Controller, useFieldArray, useForm, useWatch, type Path } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'

import type { Versioned } from '../../api/businesses'
import { deleteDraft, saveDraft, useTemplates, type InvoiceDocument } from '../../api/documents'
import { ApiError } from '../../api/http'
import { queryKeys } from '../../api/queryKeys'
import { useBusinessId } from '../../app/RequireBusiness'
import { Banner } from '../../components/ui/Banner'
import { Button } from '../../components/ui/Button'
import { cx } from '../../components/ui/cx'
import { ConfirmDialog, ConflictDialog } from '../../components/ui/Dialogs'
import { TextArea, TextField } from '../../components/ui/Field'
import { PlusIcon } from '../../components/ui/icons'
import { LeaveGuardDialog } from '../../components/ui/LeaveGuardDialog'
import { SelectField } from '../../components/ui/SelectField'
import { StatusPill } from '../../components/ui/StatusPill'
import { useToast } from '../../components/ui/Toast'
import { errorMessage } from '../../lib/errors'
import { formatDeduction, formatMoney } from '../../lib/money'
import { useUnsavedChangesGuard } from '../../lib/useUnsavedChangesGuard'
import { CustomerPicker } from './CustomerPicker'
import { EMPTY_LINE, editorSchema, MAX_LINES, toDraftFields, toEditorValues, type EditorValues } from './editorModel'
import { LineHeader, LineRow } from './LineRows'
import { useLiveTotals, type LiveTotals } from './useLiveTotals'

export interface EditorActionsSlot {
  /** Extra summary actions (Preview, Finalise) provided by later milestones. */
  render?: (state: { dirty: boolean; saving: boolean; live: LiveTotals; save: () => Promise<boolean> }) => React.ReactNode
}

/** The draft editor (docs/08 §15.2-§15.4). Amounts always come from the server. */
export function DraftEditor({ current, onReload, actions }: { current: Versioned<InvoiceDocument>; onReload: () => void; actions?: EditorActionsSlot }) {
  const businessId = useBusinessId()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const toast = useToast()
  const templates = useTemplates()
  const [conflict, setConflict] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [announcement, setAnnouncement] = useState('')
  const document = current.data

  const form = useForm<EditorValues>({
    resolver: zodResolver(editorSchema),
    defaultValues: toEditorValues(document),
    mode: 'onTouched',
  })
  const { fields, append, remove } = useFieldArray({ control: form.control, name: 'lines' })
  const lines = useWatch({ control: form.control, name: 'lines' }) ?? []
  const live = useLiveTotals(businessId, lines, document)
  const dirty = form.formState.isDirty

  const notesLength = (useWatch({ control: form.control, name: 'notes' }) ?? '').length
  const termsLength = (useWatch({ control: form.control, name: 'terms' }) ?? '').length

  const save = useMutation({
    mutationFn: (values: EditorValues) => saveDraft(document.id, toDraftFields(values), current.etag),
    onSuccess: (saved) => {
      queryClient.setQueryData(queryKeys.document(document.id), saved)
      void queryClient.invalidateQueries({ queryKey: queryKeys.documentsAll(businessId) })
      form.reset(toEditorValues(saved.data))
      setAnnouncement('Saved')
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === 'version_mismatch') setConflict(true)
      else if (error instanceof ApiError && error.code === 'document_not_draft') {
        toast.error(errorMessage(error))
        onReload()
      } else if (error instanceof ApiError && error.code === 'validation_failed') {
        let first: Path<EditorValues> | null = null
        for (const item of error.fieldErrors) {
          const path = item.pointer.replace(/^\//, '').replace(/\//g, '.').replace(/^customer_id$/, 'customer') as Path<EditorValues>
          form.setError(path, { type: 'server', message: item.message })
          first ??= path
        }
        if (first) form.setFocus(first)
      }
    },
  })

  const remove_ = useMutation({
    mutationFn: () => deleteDraft(document.id, current.etag),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: queryKeys.document(document.id) })
      void queryClient.invalidateQueries({ queryKey: queryKeys.documentsAll(businessId) })
      toast.success('Draft deleted.')
      guard.allowNextNavigation()
      navigate('/app/invoices')
    },
    onError: (error) => {
      setConfirmDelete(false)
      if (error instanceof ApiError && error.code === 'version_mismatch') setConflict(true)
      else toast.error(errorMessage(error))
    },
  })

  const guard = useUnsavedChangesGuard(dirty && !save.isPending && !remove_.isPending)

  /** Saves when needed; resolves true when the draft on the server matches the form. */
  async function saveIfNeeded(): Promise<boolean> {
    if (!form.formState.isDirty) return true
    let ok = false
    await form.handleSubmit(async (values) => {
      try {
        await save.mutateAsync(values)
        ok = true
      } catch {
        ok = false
      }
    })()
    return ok
  }

  const onSubmit = form.handleSubmit((values) => save.mutate(values))
  const saveState = save.isPending ? 'Saving…' : dirty ? 'Unsaved changes' : 'All changes saved'
  const calcProblem = live.error && !(live.error instanceof ApiError && live.error.code === 'validation_failed' && Object.keys(live.lineErrors).length)
  const totalsKnown = Boolean(live.totals) && !live.error
  const formErrors = form.formState.errors
  const genericSaveError = save.error && !(save.error instanceof ApiError && ['validation_failed', 'version_mismatch', 'document_not_draft'].includes(save.error.code))

  return (
    <form noValidate onSubmit={onSubmit} className="pb-24 lg:pb-0">
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
      <p aria-live="polite" className="sr-only">
        {live.updatedAt && !live.calculating ? 'Totals updated' : ''}
      </p>
      <header className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <nav aria-label="Breadcrumb" className="mb-2 text-sm text-ink-muted">
            <Link to="/app/invoices" className="hover:text-ink hover:underline">
              Invoices
            </Link>{' '}
            / Draft
          </nav>
          <div className="flex flex-wrap items-center gap-3">
            <h1 tabIndex={-1} className="font-serif text-2xl leading-[30px] font-semibold text-ink outline-none md:text-[30px] md:leading-9">
              Draft invoice
            </h1>
            <StatusPill tone="draft">Draft</StatusPill>
          </div>
        </div>
        <p className={cx('text-sm', dirty ? 'text-warning' : 'text-ink-muted')} aria-live="off">
          {saveState}
        </p>
      </header>

      {formErrors.root || (Object.keys(formErrors).length > 0 && form.formState.isSubmitted) ? (
        <Banner tone="danger" className="mb-4">
          Please correct the highlighted fields.
        </Banner>
      ) : null}
      {genericSaveError ? (
        <Banner tone="danger" className="mb-4">
          {errorMessage(save.error)}
        </Banner>
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_18.75rem] lg:items-start">
        <div className="flex min-w-0 flex-col gap-6">
          <section className="rounded-card border border-line bg-surface p-4 md:p-6" aria-labelledby="details-heading">
            <h2 id="details-heading" className="text-xl leading-7 font-semibold text-ink">
              Details
            </h2>
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
              <Controller
                control={form.control}
                name="customer"
                render={({ field, fieldState }) => (
                  <CustomerPicker businessId={businessId} value={field.value} onChange={(customer) => field.onChange({ id: customer.id, display_name: customer.display_name })} error={fieldState.error?.message ?? formErrors.customer?.id?.message} />
                )}
              />
              <TextField label="Reference" placeholder="For example PO-4471" error={formErrors.reference?.message} {...form.register('reference')} />
              <TextField label="Due date" type="date" min="2020-01-01" max="2099-12-31" error={formErrors.due_date?.message} {...form.register('due_date')} />
              <Controller
                control={form.control}
                name="template_id"
                render={({ field, fieldState }) => (
                  <SelectField
                    label="Template"
                    ref={field.ref}
                    value={field.value}
                    onChange={(value) => field.onChange(value ?? 'classic@1')}
                    options={(templates.data ?? [{ id: 'classic@1', name: 'Classic', tier: 'free' }]).map((t) => ({ value: t.id, label: `${t.name} · Free` }))}
                    hint="Classic is the template available in this build."
                    error={fieldState.error?.message}
                  />
                )}
              />
            </div>
          </section>

          <section className="rounded-card border border-line bg-surface p-3 md:p-4" aria-labelledby="lines-heading">
            <div className="mb-3 flex items-center justify-between px-1">
              <h2 id="lines-heading" className="text-xl leading-7 font-semibold text-ink">
                Line items
              </h2>
              <span className="text-xs text-ink-muted tabular-nums">
                {fields.length} / {MAX_LINES}
              </span>
            </div>
            {fields.length === 0 ? (
              <p className="rounded-card border border-dashed border-line px-4 py-8 text-center text-sm text-ink-muted">Add your first line item.</p>
            ) : (
              <div className="md:overflow-x-auto">
                <div className="flex flex-col gap-3 md:min-w-[49rem] md:gap-0">
                  <LineHeader />
                  {fields.map((field, index) => (
                    <LineRow key={field.id} index={index} form={form} remove={remove} live={live} disabled={save.isPending} />
                  ))}
                </div>
              </div>
            )}
            <div className="mt-3 flex flex-wrap items-center gap-3 px-1">
              <Button
                variant="secondary"
                disabled={fields.length >= MAX_LINES || save.isPending}
                onClick={() => append({ ...EMPTY_LINE }, { focusName: `lines.${fields.length}.description` })}
              >
                <PlusIcon width={18} height={18} /> Add line
              </Button>
              {fields.length >= MAX_LINES ? <span className="text-sm text-ink-muted">Maximum 200 lines</span> : null}
            </div>
          </section>

          <section className="grid grid-cols-1 gap-4 rounded-card border border-line bg-surface p-4 md:grid-cols-2 md:p-6" aria-label="Notes and terms">
            <TextArea label="Notes" maxChars={2000} currentLength={notesLength} error={formErrors.notes?.message} {...form.register('notes')} />
            <TextArea label="Terms" maxChars={2000} currentLength={termsLength} error={formErrors.terms?.message} {...form.register('terms')} />
          </section>
        </div>

        <aside className="lg:sticky lg:top-20" aria-label="Summary">
          <SummaryCard live={live} totalsKnown={totalsKnown} calcProblem={calcProblem ? live.error : null}>
            <Button type="submit" size="lg" className="w-full" disabled={!dirty} loading={save.isPending} loadingText="Saving…">
              Save draft
            </Button>
            {actions?.render?.({ dirty, saving: save.isPending, live, save: saveIfNeeded })}
            <Button variant="danger-ghost" className="w-full" onClick={() => setConfirmDelete(true)} disabled={save.isPending}>
              Delete draft
            </Button>
          </SummaryCard>
        </aside>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-between gap-3 border-t border-line bg-surface/95 px-4 py-3 backdrop-blur-sm lg:hidden">
        <div>
          <p className="text-xs text-ink-muted">Total</p>
          <p className={cx('text-lg font-semibold text-ink tabular-nums', live.calculating && 'opacity-50')}>{totalsKnown ? formatMoney(live.totals?.grand_total) : '—'}</p>
        </div>
        <Button type="submit" disabled={!dirty} loading={save.isPending} loadingText="Saving…">
          Save draft
        </Button>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Delete this draft?"
        confirmLabel="Delete draft"
        tone="danger"
        busy={remove_.isPending}
        busyLabel="Deleting…"
        onConfirm={() => remove_.mutate()}
      >
        Delete this draft? This can&apos;t be undone.
      </ConfirmDialog>
      <ConflictDialog
        open={conflict}
        onReload={() => {
          setConflict(false)
          form.reset(toEditorValues(document))
          onReload()
        }}
      />
      <LeaveGuardDialog blocker={guard.blocker} />
    </form>
  )
}

function SummaryCard({ live, totalsKnown, calcProblem, children }: { live: LiveTotals; totalsKnown: boolean; calcProblem: unknown; children: React.ReactNode }) {
  const totals = live.totals
  return (
    <section className="rounded-card border border-line bg-surface p-4 md:p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl leading-7 font-semibold text-ink">Summary</h2>
        {live.calculating ? <span className="text-xs text-ink-muted">Calculating…</span> : null}
      </div>
      <dl className={cx('mt-4 flex flex-col gap-2 text-sm transition-opacity duration-150', live.calculating && 'opacity-50')}>
        <div className="flex justify-between gap-4">
          <dt className="text-ink-muted">Subtotal</dt>
          <dd className="font-medium text-ink tabular-nums">{totalsKnown ? formatMoney(totals?.gross_total) : '—'}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-ink-muted">Discount</dt>
          <dd className="font-medium text-ink tabular-nums">{totalsKnown ? formatDeduction(totals?.discount_total) : '—'}</dd>
        </div>
        <div className="mt-2 flex items-baseline justify-between gap-4 border-t border-line pt-3">
          <dt className="text-base font-semibold text-ink">Total</dt>
          <dd key={totals?.grand_total ?? 'none'} className="value-flash rounded-control px-1 text-2xl font-semibold text-ink tabular-nums">
            {totalsKnown ? formatMoney(totals?.grand_total) : '—'}
          </dd>
        </div>
      </dl>
      <p className="mt-2 text-xs text-ink-muted">Calculated by the server · {live.calculating ? '…' : 'calc-1.0.0'}</p>
      {calcProblem ? (
        <p role="alert" className="mt-3 text-sm text-danger">
          {calcProblem instanceof ApiError && calcProblem.code === 'rate_limited'
            ? 'Please wait a moment and try again.'
            : calcProblem instanceof ApiError && calcProblem.code === 'validation_failed'
              ? (calcProblem.fieldErrors[0]?.message ?? errorMessage(calcProblem))
              : errorMessage(calcProblem)}
        </p>
      ) : null}
      <div className="mt-5 flex flex-col gap-2">{children}</div>
    </section>
  )
}
