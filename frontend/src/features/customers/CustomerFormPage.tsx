import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import type { Versioned } from '../../api/businesses'
import { createCustomer, updateCustomer, useCustomer, type Customer } from '../../api/customers'
import { ApiError } from '../../api/http'
import { queryKeys } from '../../api/queryKeys'
import { useBusinessId } from '../../app/RequireBusiness'
import { Banner } from '../../components/ui/Banner'
import { Button } from '../../components/ui/Button'
import { ConflictDialog } from '../../components/ui/Dialogs'
import { ErrorSummary, type SummaryItem } from '../../components/ui/FormBits'
import { LeaveGuardDialog } from '../../components/ui/LeaveGuardDialog'
import { PageHeader } from '../../components/ui/PageHeader'
import { DelayedSkeleton, Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { errorMessage } from '../../lib/errors'
import { applyServerErrors, changedFields } from '../../lib/forms'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { useUnsavedChangesGuard } from '../../lib/useUnsavedChangesGuard'
import { CUSTOMER_FIELDS, CUSTOMER_LABELS, CustomerFields, customerToForm, customerToInput, useCustomerForm } from './CustomerForm'

/** /app/customers/new and /app/customers/:customerId (docs/08 §14.2). */
export function CustomerFormPage() {
  const { customerId } = useParams()
  const businessId = useBusinessId()
  const customer = useCustomer(businessId, customerId)
  useDocumentTitle(customerId ? 'Edit customer' : 'New customer')

  if (customerId && customer.isPending) {
    return (
      <>
        <PageHeader title="Edit customer" />
        <DelayedSkeleton label="Loading the customer…">
          <div className="flex flex-col gap-4">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        </DelayedSkeleton>
      </>
    )
  }
  if (customerId && customer.isError) {
    const notFound = customer.error instanceof ApiError && customer.error.status === 404
    return (
      <>
        <PageHeader title="Edit customer" />
        <ErrorState
          error={customer.error}
          title={notFound ? "This customer doesn't exist or you don't have access." : undefined}
          onRetry={notFound ? undefined : () => void customer.refetch()}
        />
      </>
    )
  }
  return (
    <CustomerEditor
      key={customer.data?.etag ?? 'new'}
      businessId={businessId}
      current={customer.data}
      onReload={() => void customer.refetch()}
    />
  )
}

function CustomerEditor({ businessId, current, onReload }: { businessId: string; current?: Versioned<Customer>; onReload: () => void }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const form = useCustomerForm(current?.data)
  const [conflict, setConflict] = useState(false)
  const [summary, setSummary] = useState<{ items: SummaryItem[]; extra: string[] } | null>(null)

  const save = useMutation({
    mutationFn: (values: ReturnType<typeof customerToForm>) => {
      const input = customerToInput(values)
      if (current) return updateCustomer(businessId, current.data.id, changedFields(input, current.data), current.etag)
      return createCustomer(businessId, input)
    },
    onSuccess: async (saved) => {
      queryClient.setQueryData(queryKeys.customer(saved.data.id), saved)
      await queryClient.invalidateQueries({ queryKey: queryKeys.customersAll(businessId) })
      form.reset(customerToForm(saved.data))
      toast.success('Customer saved.')
      guard.allowNextNavigation()
      navigate('/app/customers')
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === 'version_mismatch') {
        setConflict(true)
        return
      }
      const extra = applyServerErrors(form, error, CUSTOMER_FIELDS)
      if (error instanceof ApiError && error.code === 'validation_failed') {
        setSummary({
          items: CUSTOMER_FIELDS.flatMap((field) => {
            const message = form.getFieldState(field).error?.message
            return message ? [{ field, label: CUSTOMER_LABELS[field], message }] : []
          }),
          extra,
        })
      }
    },
  })
  const guard = useUnsavedChangesGuard(form.formState.isDirty && !save.isPending)

  const submit = form.handleSubmit(
    (values) => save.mutate(values),
    (invalid) =>
      setSummary({
        items: CUSTOMER_FIELDS.flatMap((field) => {
          const message = invalid[field]?.message
          return message ? [{ field, label: CUSTOMER_LABELS[field], message }] : []
        }),
        extra: [],
      }),
  )
  const genericError = save.error && !(save.error instanceof ApiError && ['validation_failed', 'version_mismatch'].includes(save.error.code))

  return (
    <>
      <PageHeader title={current ? current.data.display_name : 'New customer'} eyebrow={current ? 'Edit customer' : undefined} />
      <form noValidate onSubmit={submit} className="flex flex-col gap-6">
        {current ? (
          <Banner tone="info">Changes apply to drafts and new invoices. Issued invoices keep the details they were issued with.</Banner>
        ) : null}
        {summary ? <ErrorSummary items={summary.items} extra={summary.extra} onFocus={(field) => form.setFocus(field as (typeof CUSTOMER_FIELDS)[number])} /> : null}
        {genericError ? <Banner tone="danger">{errorMessage(save.error)}</Banner> : null}
        <fieldset disabled={save.isPending} className="flex flex-col gap-6">
          <CustomerFields form={form} />
        </fieldset>
        <div className="sticky bottom-0 -mx-4 flex items-center justify-end gap-3 border-t border-line bg-paper/95 px-4 py-3 backdrop-blur-sm md:static md:mx-0 md:border-0 md:bg-transparent md:p-0">
          <Button variant="secondary" size="lg" onClick={() => navigate('/app/customers')}>
            Cancel
          </Button>
          <Button type="submit" size="lg" disabled={Boolean(current) && !form.formState.isDirty} loading={save.isPending} loadingText="Saving…">
            Save customer
          </Button>
        </div>
      </form>
      <ConflictDialog
        open={conflict}
        onReload={() => {
          setConflict(false)
          onReload()
        }}
      />
      <LeaveGuardDialog blocker={guard.blocker} />
    </>
  )
}
