import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm, type UseFormReturn } from 'react-hook-form'
import { z } from 'zod'

import type { Customer, CustomerInput } from '../../api/customers'
import { TextField } from '../../components/ui/Field'
import { FormSection } from '../../components/ui/FormBits'
import { SelectField } from '../../components/ui/SelectField'
import { optional } from '../../lib/forms'
import { STATES_BY_NAME } from '../../lib/states'

const GSTIN = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/
const PHONE = /^[0-9+() -]{6,20}$/
const EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

export const customerSchema = z
  .object({
    display_name: z.string().trim().min(1, 'Enter the customer name.').max(200, 'Use at most 200 characters.'),
    contact_name: z.string().trim().max(120, 'Use at most 120 characters.'),
    email: z
      .string()
      .trim()
      .max(254, 'Use at most 254 characters.')
      .refine((v) => v === '' || EMAIL.test(v), 'Enter an email address such as name@example.com.'),
    phone: z.string().trim().refine((v) => v === '' || PHONE.test(v), 'Use 6–20 characters: digits, spaces, +, - and brackets.'),
    address_line1: z.string().trim().max(200, 'Use at most 200 characters.'),
    address_line2: z.string().trim().max(200, 'Use at most 200 characters.'),
    city: z.string().trim().max(100, 'Use at most 100 characters.'),
    state_code: z.string(),
    postal_code: z.string().trim().refine((v) => v === '' || /^[1-9][0-9]{5}$/.test(v), 'Enter a 6-digit PIN code that does not start with 0.'),
    gstin: z
      .string()
      .trim()
      .refine((v) => v === '' || GSTIN.test(v.toUpperCase()), 'Enter a 15-character GSTIN, for example 27ABCDE1234F1Z5.'),
  })
  .superRefine((values, ctx) => {
    const gstin = values.gstin.trim().toUpperCase()
    if (gstin && values.state_code && GSTIN.test(gstin) && gstin.slice(0, 2) !== values.state_code) {
      ctx.addIssue({ code: 'custom', path: ['gstin'], message: 'The first two digits of the GSTIN must match the state code.' })
    }
  })

export type CustomerFormValues = z.infer<typeof customerSchema>

export const CUSTOMER_FIELDS = [
  'display_name', 'contact_name', 'email', 'phone', 'address_line1', 'address_line2', 'city', 'state_code', 'postal_code', 'gstin',
] as const

export const CUSTOMER_LABELS: Record<(typeof CUSTOMER_FIELDS)[number], string> = {
  display_name: 'Display name',
  contact_name: 'Contact name',
  email: 'Email',
  phone: 'Phone',
  address_line1: 'Address line 1',
  address_line2: 'Address line 2',
  city: 'City',
  state_code: 'State',
  postal_code: 'PIN code',
  gstin: 'GSTIN',
}

export function customerToForm(customer?: Customer): CustomerFormValues {
  return {
    display_name: customer?.display_name ?? '',
    contact_name: customer?.contact_name ?? '',
    email: customer?.email ?? '',
    phone: customer?.phone ?? '',
    address_line1: customer?.address_line1 ?? '',
    address_line2: customer?.address_line2 ?? '',
    city: customer?.city ?? '',
    state_code: customer?.state_code ?? '',
    postal_code: customer?.postal_code ?? '',
    gstin: customer?.gstin ?? '',
  }
}

export function customerToInput(values: CustomerFormValues): CustomerInput {
  return {
    display_name: values.display_name.trim(),
    contact_name: optional(values.contact_name),
    email: optional(values.email),
    phone: optional(values.phone),
    address_line1: optional(values.address_line1),
    address_line2: optional(values.address_line2),
    city: optional(values.city),
    state_code: values.state_code || null,
    postal_code: optional(values.postal_code),
    gstin: optional(values.gstin)?.toUpperCase() ?? null,
  }
}

export function useCustomerForm(customer?: Customer) {
  return useForm<CustomerFormValues>({
    resolver: zodResolver(customerSchema),
    defaultValues: customerToForm(customer),
    mode: 'onTouched',
  })
}

/** The customer fields of docs/08 §14.2, in sections. */
export function CustomerFields({ form }: { form: UseFormReturn<CustomerFormValues> }) {
  const errors = form.formState.errors
  return (
    <>
      <FormSection title="Customer">
        <TextField label="Display name" required frameClassName="md:col-span-2" error={errors.display_name?.message} {...form.register('display_name')} />
        <TextField label="Contact name" autoComplete="name" error={errors.contact_name?.message} {...form.register('contact_name')} />
        <TextField label="Email" type="email" autoComplete="email" error={errors.email?.message} {...form.register('email')} />
        <TextField label="Phone" type="tel" autoComplete="tel" error={errors.phone?.message} {...form.register('phone')} />
      </FormSection>
      <FormSection title="Address">
        <TextField label="Address line 1" frameClassName="md:col-span-2" autoComplete="address-line1" error={errors.address_line1?.message} {...form.register('address_line1')} />
        <TextField label="Address line 2" frameClassName="md:col-span-2" autoComplete="address-line2" error={errors.address_line2?.message} {...form.register('address_line2')} />
        <TextField label="City" autoComplete="address-level2" error={errors.city?.message} {...form.register('city')} />
        <Controller
          control={form.control}
          name="state_code"
          render={({ field, fieldState }) => (
            <SelectField
              label="State"
              ref={field.ref}
              value={field.value || null}
              onChange={(value) => field.onChange(value ?? '')}
              onBlur={field.onBlur}
              options={STATES_BY_NAME.map(([code, name]) => ({ value: code, label: name }))}
              allowEmpty="Not set"
              error={fieldState.error?.message}
            />
          )}
        />
        <TextField label="PIN code" inputMode="numeric" autoComplete="postal-code" maxLength={6} error={errors.postal_code?.message} {...form.register('postal_code')} />
      </FormSection>
      <FormSection title="Tax identifier (optional)">
        <TextField
          label="GSTIN"
          className="uppercase"
          autoCapitalize="characters"
          spellCheck={false}
          maxLength={15}
          hint="Optional. Must match the state when both are given."
          error={errors.gstin?.message}
          {...form.register('gstin')}
        />
      </FormSection>
    </>
  )
}
