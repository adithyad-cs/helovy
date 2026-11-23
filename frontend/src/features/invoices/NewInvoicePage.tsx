import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router'

import type { CustomerSummary } from '../../api/customers'
import { useCustomerList } from '../../api/customers'
import { createDraft } from '../../api/documents'
import { queryKeys } from '../../api/queryKeys'
import { useBusinessId } from '../../app/RequireBusiness'
import { Banner } from '../../components/ui/Banner'
import { Button } from '../../components/ui/Button'
import { PlusIcon, UsersIcon } from '../../components/ui/icons'
import { PageHeader } from '../../components/ui/PageHeader'
import { DelayedSkeleton, Skeleton } from '../../components/ui/Skeleton'
import { EmptyState, ErrorState } from '../../components/ui/States'
import { Spinner } from '../../components/ui/Spinner'
import { errorMessage } from '../../lib/errors'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { CustomerPicker } from './CustomerPicker'
import { QuickCustomerDialog } from './QuickCustomerDialog'

/** /app/invoices/new (docs/08 §15.1): choose a customer, then create the draft (E-15). */
export function NewInvoicePage() {
  useDocumentTitle('New invoice')
  const businessId = useBusinessId()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [quickOpen, setQuickOpen] = useState(false)
  const anyCustomer = useCustomerList(businessId, '', 1)

  const create = useMutation({
    mutationFn: (customerId: string) => createDraft(businessId, customerId),
    onSuccess: (draft) => {
      queryClient.setQueryData(queryKeys.document(draft.data.id), draft)
      void queryClient.invalidateQueries({ queryKey: queryKeys.documentsAll(businessId) })
      navigate(`/app/invoices/${draft.data.id}`, { replace: true })
    },
  })

  const hasCustomers = (anyCustomer.data?.pages[0]?.items.length ?? 0) > 0

  return (
    <>
      <PageHeader title="New invoice" eyebrow="Invoices / New" description="Choose who you are billing. A draft is created straight away and can be changed until you finalise it." />
      {anyCustomer.isPending ? (
        <DelayedSkeleton label="Loading customers…">
          <Skeleton className="h-32 w-full max-w-xl" />
        </DelayedSkeleton>
      ) : anyCustomer.isError ? (
        <ErrorState error={anyCustomer.error} onRetry={() => void anyCustomer.refetch()} />
      ) : !hasCustomers ? (
        <EmptyState
          icon={<UsersIcon width={28} height={28} />}
          title="Add a customer first."
          action={
            <Button onClick={() => setQuickOpen(true)}>
              <PlusIcon width={18} height={18} /> New customer
            </Button>
          }
        >
          Every invoice is addressed to one of your customers.
        </EmptyState>
      ) : (
        <section className="card-enter max-w-xl rounded-card border border-line bg-surface p-4 md:p-6">
          <h2 className="text-xl font-semibold text-ink">Choose a customer</h2>
          <div className="mt-4 flex flex-col gap-4">
            <CustomerPicker
              businessId={businessId}
              value={null}
              disabled={create.isPending}
              onChange={(customer: CustomerSummary) => create.mutate(customer.id)}
            />
            {create.isPending ? (
              <p role="status" className="flex items-center gap-2 text-sm text-ink-muted">
                <Spinner /> Creating the draft…
              </p>
            ) : null}
            {create.error ? <Banner tone="danger">{errorMessage(create.error)}</Banner> : null}
            <p className="text-sm text-ink-muted">
              Not in the list?{' '}
              <button type="button" className="font-medium text-accent underline underline-offset-2 hover:text-accent-hover" onClick={() => setQuickOpen(true)}>
                Add a new customer
              </button>
            </p>
          </div>
        </section>
      )}
      <QuickCustomerDialog businessId={businessId} open={quickOpen} onOpenChange={setQuickOpen} onCreated={(customer) => create.mutate(customer.id)} />
    </>
  )
}
