import { Select } from 'radix-ui'
import { Controller, useFormState, type UseFieldArrayRemove, type UseFormReturn } from 'react-hook-form'

import { cx } from '../../components/ui/cx'
import { controlClasses } from '../../components/ui/Field'
import { CheckIcon, ChevronDownIcon, TrashIcon } from '../../components/ui/icons'
import { formatMoney } from '../../lib/money'
import type { EditorValues } from './editorModel'
import type { LiveTotals } from './useLiveTotals'

/** Columns from 768 px; the grid scrolls horizontally inside its frame if needed (docs/11 FE-05). */
export const LINE_GRID =
  'md:grid md:grid-cols-[1.75rem_minmax(10rem,1fr)_5rem_4rem_7rem_10rem_7rem_2.5rem] md:items-start md:gap-x-1.5'

const LABEL = 'mb-1 block text-xs font-medium text-ink-muted md:sr-only'

export function LineHeader() {
  return (
    <div aria-hidden="true" className={cx(LINE_GRID, 'hidden border-b border-line px-3 pb-2 text-xs font-medium tracking-wide text-ink-muted uppercase')}>
      <span>#</span>
      <span>Description</span>
      <span className="text-right">Qty</span>
      <span>Unit</span>
      <span className="text-right">Unit price (₹)</span>
      <span>Discount</span>
      <span className="text-right">Amount</span>
      <span />
    </div>
  )
}

interface LineRowProps {
  index: number
  form: UseFormReturn<EditorValues>
  remove: UseFieldArrayRemove
  live: LiveTotals
  disabled: boolean
}

export function LineRow({ index, form, remove, live, disabled }: LineRowProps) {
  const { errors } = useFormState({ control: form.control, name: `lines.${index}` })
  const lineErrors = errors.lines?.[index]
  const serverErrors = live.lineErrors[index] ?? {}
  const amounts = live.lines[index]
  const discountType = form.watch(`lines.${index}.discount_type`)
  const id = (field: string) => `line-${index}-${field}`
  const message = (field: 'description' | 'quantity' | 'unit' | 'unit_price' | 'discount_value') =>
    lineErrors?.[field]?.message ?? serverErrors[field]
  const describe = (field: Parameters<typeof message>[0]) => (message(field) ? `${id(field)}-error` : undefined)

  return (
    <div role="group" aria-label={`Line ${index + 1}`} className={cx(LINE_GRID, 'relative rounded-card border border-line bg-surface p-3 md:rounded-none md:border-0 md:border-b md:bg-transparent md:px-3 md:py-2.5')}>
      <div className="mb-2 flex items-center justify-between md:mb-0 md:block md:pt-2.5">
        <span className="text-sm font-semibold text-ink-muted tabular-nums">
          <span className="md:hidden">Line </span>
          {index + 1}
        </span>
      </div>

      <div className="mb-3 md:mb-0">
        <label htmlFor={id('description')} className={LABEL}>
          Description (required)
        </label>
        <textarea
          id={id('description')}
          rows={2}
          disabled={disabled}
          aria-invalid={message('description') ? true : undefined}
          aria-describedby={describe('description')}
          className={controlClasses(Boolean(message('description')), 'min-h-[4.25rem] resize-y py-2 leading-5')}
          {...form.register(`lines.${index}.description`)}
        />
        <FieldMessage id={`${id('description')}-error`} text={message('description')} />
      </div>

      <div className="grid grid-cols-2 gap-3 md:contents">
        <div>
          <label htmlFor={id('quantity')} className={LABEL}>
            Quantity
          </label>
          <input
            id={id('quantity')}
            inputMode="decimal"
            autoComplete="off"
            disabled={disabled}
            aria-invalid={message('quantity') ? true : undefined}
            aria-describedby={describe('quantity')}
            className={controlClasses(Boolean(message('quantity')), 'min-h-10 py-2 text-right tabular-nums')}
            {...form.register(`lines.${index}.quantity`)}
          />
          <FieldMessage id={`${id('quantity')}-error`} text={message('quantity')} />
        </div>
        <div>
          <label htmlFor={id('unit')} className={LABEL}>
            Unit
          </label>
          <input
            id={id('unit')}
            autoComplete="off"
            placeholder="hrs"
            disabled={disabled}
            aria-invalid={message('unit') ? true : undefined}
            aria-describedby={describe('unit')}
            className={controlClasses(Boolean(message('unit')), 'min-h-10 py-2')}
            {...form.register(`lines.${index}.unit`)}
          />
          <FieldMessage id={`${id('unit')}-error`} text={message('unit')} />
        </div>
        <div className="col-span-2 md:col-span-1">
          <label htmlFor={id('unit_price')} className={LABEL}>
            Unit price (₹)
          </label>
          <input
            id={id('unit_price')}
            inputMode="decimal"
            autoComplete="off"
            placeholder="0.00"
            disabled={disabled}
            aria-invalid={message('unit_price') ? true : undefined}
            aria-describedby={describe('unit_price')}
            className={controlClasses(Boolean(message('unit_price')), 'min-h-10 py-2 text-right tabular-nums')}
            {...form.register(`lines.${index}.unit_price`)}
          />
          <FieldMessage id={`${id('unit_price')}-error`} text={message('unit_price')} />
        </div>
        <div className="col-span-2 md:col-span-1">
          <span id={id('discount')} className={LABEL}>
            Discount
          </span>
          <div className="flex gap-1.5">
            <Controller
              control={form.control}
              name={`lines.${index}.discount_type`}
              render={({ field }) => (
                <Select.Root
                  value={field.value}
                  onValueChange={(value) => {
                    field.onChange(value)
                    if (value === 'none') form.setValue(`lines.${index}.discount_value`, '', { shouldDirty: true })
                  }}
                  disabled={disabled}
                >
                  <Select.Trigger
                    ref={field.ref}
                    aria-label={`Discount type, line ${index + 1}`}
                    className={controlClasses(false, 'flex min-h-10 shrink-0 items-center justify-between gap-1 px-2 py-2').replace('w-full', 'w-[4.25rem]')}
                  >
                    <Select.Value />
                    <ChevronDownIcon width={14} height={14} className="text-ink-muted" />
                  </Select.Trigger>
                  <Select.Portal>
                    <Select.Content position="popper" sideOffset={4} className="popover-enter z-50 min-w-[9rem] rounded-card border border-line bg-surface p-1 shadow-[0_8px_24px_rgba(27,42,65,0.14)]">
                      <Select.Viewport>
                        {(
                          [
                            ['none', 'None', 'No discount'],
                            ['percent', '%', 'Percent (%)'],
                            ['amount', '₹', 'Amount (₹)'],
                          ] as const
                        ).map(([value, short, long]) => (
                          <Select.Item
                            key={value}
                            value={value}
                            className="relative flex min-h-9 cursor-pointer items-center rounded-control py-1.5 pr-3 pl-7 text-sm text-ink outline-none data-[highlighted]:bg-tint-neutral"
                          >
                            <Select.ItemIndicator className="absolute left-1.5 text-accent">
                              <CheckIcon width={14} height={14} />
                            </Select.ItemIndicator>
                            <Select.ItemText>{short}</Select.ItemText>
                            <span className="ml-2 text-xs text-ink-muted">{long}</span>
                          </Select.Item>
                        ))}
                      </Select.Viewport>
                    </Select.Content>
                  </Select.Portal>
                </Select.Root>
              )}
            />
            <input
              inputMode="decimal"
              autoComplete="off"
              aria-label={`Discount value, line ${index + 1}`}
              placeholder={discountType === 'percent' ? '10' : discountType === 'amount' ? '0.00' : '—'}
              disabled={disabled || discountType === 'none'}
              aria-invalid={message('discount_value') ? true : undefined}
              aria-describedby={describe('discount_value')}
              className={controlClasses(Boolean(message('discount_value')), 'min-h-10 min-w-0 flex-1 py-2 text-right tabular-nums')}
              {...form.register(`lines.${index}.discount_value`)}
            />
          </div>
          <FieldMessage id={`${id('discount_value')}-error`} text={message('discount_value')} />
        </div>
      </div>

      <div className="mt-3 flex items-baseline justify-between border-t border-line pt-3 md:mt-0 md:block md:border-0 md:pt-2.5 md:text-right">
        <span className="text-sm text-ink-muted md:sr-only">Amount</span>
        <span
          key={amounts?.line_total ?? 'none'}
          className={cx('value-flash rounded-control px-1 text-base font-semibold text-ink tabular-nums transition-opacity duration-150 md:text-sm', live.calculating && 'opacity-50')}
        >
          {amounts && !serverErrors.quantity && !serverErrors.unit_price && !serverErrors.discount_value ? formatMoney(amounts.line_total) : '—'}
        </span>
        {amounts && amounts.discount !== '0.00' ? (
          <span className="block text-xs text-ink-muted tabular-nums md:mt-0.5">
            {formatMoney(amounts.gross)} − {formatMoney(amounts.discount)}
          </span>
        ) : null}
      </div>

      <div className="absolute top-2 right-2 md:static md:pt-1">
        <button
          type="button"
          onClick={() => remove(index)}
          disabled={disabled}
          aria-label={`Remove line ${index + 1}`}
          className="flex h-9 w-9 items-center justify-center rounded-control text-ink-muted transition-colors hover:bg-tint-danger hover:text-danger disabled:opacity-50"
        >
          <TrashIcon width={18} height={18} />
        </button>
      </div>
    </div>
  )
}

function FieldMessage({ id, text }: { id: string; text?: string }) {
  if (!text) return null
  return (
    <p id={id} className="mt-1 text-xs text-danger">
      {text}
    </p>
  )
}
