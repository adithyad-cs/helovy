import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Dialog } from 'radix-ui'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { createCustomer, type Customer } from '../../api/customers'
import { queryKeys } from '../../api/queryKeys'
import { Banner } from '../../components/ui/Banner'
import { Button } from '../../components/ui/Button'
import { TextField } from '../../components/ui/Field'
import { useToast } from '../../components/ui/Toast'
import { errorMessage } from '../../lib/errors'
import { applyServerErrors, optional } from '../../lib/forms'

const schema = z.object({
  display_name: z.string().trim().min(1, 'Enter the customer name.').max(200, 'Use at most 200 characters.'),
  email: z
    .string()
    .trim()
    .max(254, 'Use at most 254 characters.')
    .refine((v) => v === '' || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v), 'Enter an email address such as name@example.com.'),
  city: z.string().trim().max(100, 'Use at most 100 characters.'),
})
type Values = z.infer<typeof schema>

/** Quick create from the invoice editor (docs/08 §14.2): name, email and city → E-10. */
export function QuickCustomerDialog({
  businessId,
  open,
  onOpenChange,
  onCreated,
}: {
  businessId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (customer: Customer) => void
}) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { display_name: '', email: '', city: '' } })
  const create = useMutation({
    mutationFn: (values: Values) =>
      createCustomer(businessId, { display_name: values.display_name.trim(), email: optional(values.email), city: optional(values.city) }),
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.customersAll(businessId) })
      toast.success('Customer saved.')
      form.reset()
      onCreated(saved.data)
      onOpenChange(false)
    },
    onError: (error) => applyServerErrors(form, error, ['display_name', 'email', 'city']),
  })
  const errors = form.formState.errors

  return (
    <Dialog.Root open={open} onOpenChange={(next) => (create.isPending ? undefined : onOpenChange(next))}>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay-enter fixed inset-0 z-40 bg-ink/40" />
        <Dialog.Content className="dialog-enter fixed top-1/2 left-1/2 z-50 w-[calc(100vw-32px)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-card bg-surface p-6 shadow-[0_16px_48px_rgba(27,42,65,0.22)] outline-none">
          <Dialog.Title className="font-serif text-xl font-semibold text-ink">New customer</Dialog.Title>
          <Dialog.Description className="mt-1 text-sm text-ink-muted">
            Add the essentials now; you can complete the address later on the Customers page.
          </Dialog.Description>
          <form noValidate className="mt-4 flex flex-col gap-4" onSubmit={form.handleSubmit((values) => create.mutate(values))}>
            {create.error && !applyServerErrorsSafe(create.error) ? <Banner tone="danger">{errorMessage(create.error)}</Banner> : null}
            <fieldset disabled={create.isPending} className="flex flex-col gap-4">
              <TextField label="Display name" required autoFocus error={errors.display_name?.message} {...form.register('display_name')} />
              <TextField label="Email" type="email" error={errors.email?.message} {...form.register('email')} />
              <TextField label="City" error={errors.city?.message} {...form.register('city')} />
            </fieldset>
            <div className="mt-2 flex flex-col-reverse gap-2 md:flex-row md:justify-end">
              <Dialog.Close asChild>
                <Button variant="secondary" disabled={create.isPending}>
                  Cancel
                </Button>
              </Dialog.Close>
              <Button type="submit" loading={create.isPending} loadingText="Saving…">
                Save customer
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function applyServerErrorsSafe(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'code' in error && (error as { code: string }).code === 'validation_failed'
}
