import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'
import { useLocation, useNavigate } from 'react-router'
import { z } from 'zod'

import { useMe } from '../../api/auth'
import { createBusiness, updateBusiness, useBusiness, type Business, type BusinessInput, type Versioned } from '../../api/businesses'
import { ApiError } from '../../api/http'
import { queryKeys } from '../../api/queryKeys'
import { Banner } from '../../components/ui/Banner'
import { Button } from '../../components/ui/Button'
import { ConflictDialog } from '../../components/ui/Dialogs'
import { TextField } from '../../components/ui/Field'
import { ErrorSummary, FormSection, type SummaryItem } from '../../components/ui/FormBits'
import { LeaveGuardDialog } from '../../components/ui/LeaveGuardDialog'
import { PageHeader } from '../../components/ui/PageHeader'
import { SelectField } from '../../components/ui/SelectField'
import { DelayedSkeleton, Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/ui/States'
import { useToast } from '../../components/ui/Toast'
import { errorMessage } from '../../lib/errors'
import { applyServerErrors, changedFields, optional } from '../../lib/forms'
import { STATES_BY_NAME } from '../../lib/states'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { useUnsavedChangesGuard } from '../../lib/useUnsavedChangesGuard'

const GSTIN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/
const PHONE = /^[0-9+() -]{6,20}$/
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

const schema = z
  .object({
    legal_name: z.string().trim().min(1, 'Enter the legal name.').max(200, 'Use at most 200 characters.'),
    trade_name: z.string().trim().max(200, 'Use at most 200 characters.'),
    address_line1: z.string().trim().min(1, 'Enter the first address line.').max(200, 'Use at most 200 characters.'),
    address_line2: z.string().trim().max(200, 'Use at most 200 characters.'),
    city: z.string().trim().min(1, 'Enter the city.').max(100, 'Use at most 100 characters.'),
    state_code: z.string().min(1, 'Choose a state.'),
    postal_code: z.string().trim().regex(/^[1-9][0-9]{5}$/, 'Enter a 6-digit PIN code that does not start with 0.'),
    phone: z.string().trim().refine((v) => v === '' || PHONE.test(v), 'Use 6–20 characters: digits, spaces, +, - and brackets.'),
    email: z
      .string()
      .trim()
      .max(254, 'Use at most 254 characters.')
      .refine((v) => v === '' || EMAIL.test(v), 'Enter an email address such as name@example.com.'),
    gstin: z
      .string()
      .trim()
      .refine((v) => v === '' || GSTIN.test(v.toUpperCase()), 'Enter a 15-character GSTIN, for example 29ABCDE1234F1Z5.'),
  })
  .superRefine((values, ctx) => {
    const gstin = values.gstin.trim().toUpperCase()
    if (gstin && values.state_code && GSTIN.test(gstin) && gstin.slice(0, 2) !== values.state_code) {
      ctx.addIssue({ code: 'custom', path: ['gstin'], message: 'The first two digits of the GSTIN must match the state code.' })
    }
  })

type FormValues = z.infer<typeof schema>

const FIELDS = ['legal_name', 'trade_name', 'address_line1', 'address_line2', 'city', 'state_code', 'postal_code', 'phone', 'email', 'gstin'] as const
const LABELS: Record<(typeof FIELDS)[number], string> = {
  legal_name: 'Legal name',
  trade_name: 'Trade name',
  address_line1: 'Address line 1',
  address_line2: 'Address line 2',
  city: 'City',
  state_code: 'State',
  postal_code: 'PIN code',
  phone: 'Phone',
  email: 'Email',
  gstin: 'GSTIN',
}

function toForm(business?: Business): FormValues {
  return {
    legal_name: business?.legal_name ?? '',
    trade_name: business?.trade_name ?? '',
    address_line1: business?.address_line1 ?? '',
    address_line2: business?.address_line2 ?? '',
    city: business?.city ?? '',
    state_code: business?.state_code ?? '',
    postal_code: business?.postal_code ?? '',
    phone: business?.phone ?? '',
    email: business?.email ?? '',
    gstin: business?.gstin ?? '',
  }
}

function toInput(values: FormValues): BusinessInput {
  return {
    legal_name: values.legal_name.trim(),
    trade_name: optional(values.trade_name),
    address_line1: values.address_line1.trim(),
    address_line2: optional(values.address_line2),
    city: values.city.trim(),
    state_code: values.state_code,
    postal_code: values.postal_code.trim(),
    phone: optional(values.phone),
    email: optional(values.email),
    gstin: optional(values.gstin)?.toUpperCase() ?? null,
  }
}

/** /app/business (docs/08 §13): create once, then edit with If-Match. */
export function BusinessProfilePage() {
  useDocumentTitle('Business profile')
  const me = useMe()
  const businessId = me.data?.business?.id
  const business = useBusiness(businessId)
  const location = useLocation()
  const required = (location.state as { reason?: string } | null)?.reason === 'business-required'

  return (
    <>
      <PageHeader
        title="Business profile"
        description={businessId ? undefined : 'Your business details appear on every invoice.'}
      />
      {required && !businessId ? (
        <Banner tone="warning" className="mb-6">
          Set up your business first.
        </Banner>
      ) : null}
      {businessId && business.isPending ? (
        <DelayedSkeleton label="Loading the business profile…">
          <div className="flex flex-col gap-4">
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-56 w-full" />
          </div>
        </DelayedSkeleton>
      ) : businessId && business.isError ? (
        <ErrorState error={business.error} onRetry={() => void business.refetch()} />
      ) : (
        <BusinessForm key={business.data?.etag ?? 'new'} current={business.data} onReload={() => void business.refetch()} />
      )}
    </>
  )
}

function BusinessForm({ current, onReload }: { current?: Versioned<Business>; onReload: () => void }) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const toast = useToast()
  const [conflict, setConflict] = useState(false)
  const [summary, setSummary] = useState<{ items: SummaryItem[]; extra: string[] } | null>(null)
  const editing = Boolean(current)
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: toForm(current?.data), mode: 'onTouched' })
  const { isDirty, errors } = form.formState

  const save = useMutation({
    mutationFn: async (values: FormValues) => {
      const input = toInput(values)
      if (current) return updateBusiness(current.data.id, changedFields(input, current.data), current.etag)
      return createBusiness(input)
    },
    onSuccess: async (saved) => {
      queryClient.setQueryData(queryKeys.business(saved.data.id), saved)
      await queryClient.invalidateQueries({ queryKey: queryKeys.me })
      form.reset(toForm(saved.data))
      setSummary(null)
      toast.success('Business profile saved.')
      if (!editing) {
        guard.allowNextNavigation()
        navigate('/app')
      }
    },
    onError: async (error) => {
      if (error instanceof ApiError && error.code === 'version_mismatch') {
        setConflict(true)
        return
      }
      if (error instanceof ApiError && error.code === 'business_already_exists') {
        toast.error(errorMessage(error))
        await queryClient.invalidateQueries({ queryKey: queryKeys.me })
        return
      }
      const extra = applyServerErrors(form, error, FIELDS)
      if (error instanceof ApiError && error.code === 'validation_failed') {
        setSummary({ items: summaryItems(form.getFieldState), extra })
      }
    },
  })

  const guard = useUnsavedChangesGuard(isDirty && !save.isPending)

  function summaryItems(getState: typeof form.getFieldState): SummaryItem[] {
    return FIELDS.flatMap((field) => {
      const message = getState(field).error?.message
      return message ? [{ field, label: LABELS[field], message }] : []
    })
  }

  const submit = form.handleSubmit(
    (values) => save.mutate(values),
    (invalid) => {
      setSummary({
        items: FIELDS.flatMap((field) => {
          const message = invalid[field]?.message
          return message ? [{ field, label: LABELS[field], message }] : []
        }),
        extra: [],
      })
    },
  )

  const genericError = save.error && !(save.error instanceof ApiError && ['validation_failed', 'version_mismatch', 'business_already_exists'].includes(save.error.code))

  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-6">
      {editing ? <Banner tone="info">Issued invoices keep the details they were issued with.</Banner> : null}
      {summary ? <ErrorSummary items={summary.items} extra={summary.extra} onFocus={(field) => form.setFocus(field as keyof FormValues)} /> : null}
      {genericError ? (
        <Banner tone="danger">{errorMessage(save.error)}</Banner>
      ) : null}

      <fieldset disabled={save.isPending} className="flex flex-col gap-6">
        <FormSection title="Business details">
          <TextField label="Legal name" required autoComplete="organization" error={errors.legal_name?.message} {...form.register('legal_name')} />
          <TextField label="Trade name" error={errors.trade_name?.message} {...form.register('trade_name')} />
        </FormSection>

        <FormSection title="Address">
          <TextField label="Address line 1" required autoComplete="address-line1" frameClassName="md:col-span-2" error={errors.address_line1?.message} {...form.register('address_line1')} />
          <TextField label="Address line 2" autoComplete="address-line2" frameClassName="md:col-span-2" error={errors.address_line2?.message} {...form.register('address_line2')} />
          <TextField label="City" required autoComplete="address-level2" error={errors.city?.message} {...form.register('city')} />
          <Controller
            control={form.control}
            name="state_code"
            render={({ field, fieldState }) => (
              <SelectField
                label="State"
                required
                ref={field.ref}
                value={field.value || null}
                onChange={(value) => field.onChange(value ?? '')}
                onBlur={field.onBlur}
                options={STATES_BY_NAME.map(([code, name]) => ({ value: code, label: name }))}
                placeholder="Choose a state"
                error={fieldState.error?.message}
              />
            )}
          />
          <TextField label="PIN code" required inputMode="numeric" autoComplete="postal-code" maxLength={6} error={errors.postal_code?.message} {...form.register('postal_code')} />
        </FormSection>

        <FormSection title="Contact">
          <TextField label="Phone" type="tel" autoComplete="tel" error={errors.phone?.message} {...form.register('phone')} />
          <TextField label="Email" type="email" autoComplete="email" error={errors.email?.message} {...form.register('email')} />
        </FormSection>

        <FormSection title="Tax identifier (optional)">
          <TextField
            label="GSTIN"
            className="uppercase"
            autoCapitalize="characters"
            spellCheck={false}
            maxLength={15}
            hint="Optional. Printed on your documents if provided. This demonstration does not calculate GST."
            error={errors.gstin?.message}
            {...form.register('gstin')}
          />
        </FormSection>
      </fieldset>

      <div className="sticky bottom-0 -mx-4 flex items-center justify-end gap-3 border-t border-line bg-paper/95 px-4 py-3 backdrop-blur-sm md:static md:mx-0 md:border-0 md:bg-transparent md:p-0">
        {editing && isDirty ? <span className="mr-auto text-sm text-ink-muted">Unsaved changes</span> : null}
        <Button type="submit" size="lg" disabled={!isDirty} loading={save.isPending} loadingText="Saving…">
          {editing ? 'Save changes' : 'Save business'}
        </Button>
      </div>

      <ConflictDialog
        open={conflict}
        onReload={() => {
          setConflict(false)
          onReload()
        }}
      />
      <LeaveGuardDialog blocker={guard.blocker} />
    </form>
  )
}
