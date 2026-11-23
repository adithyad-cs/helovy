import { Select } from 'radix-ui'
import { forwardRef, useId, type ReactNode } from 'react'

import { cx } from './cx'
import { controlClasses, describedBy, FieldFrame } from './Field'
import { CheckIcon, ChevronDownIcon } from './icons'

export interface SelectOption {
  value: string
  label: string
}

const NONE = '__none__'

interface SelectFieldProps {
  label: ReactNode
  value: string | null
  onChange: (value: string | null) => void
  options: ReadonlyArray<SelectOption>
  placeholder?: string
  required?: boolean
  error?: string
  hint?: ReactNode
  allowEmpty?: string
  disabled?: boolean
  name?: string
  onBlur?: () => void
}

/** Radix Select with a visible label (docs/08 §2). `allowEmpty` adds a "none" choice. */
export const SelectField = forwardRef<HTMLButtonElement, SelectFieldProps>(function SelectField(
  { label, value, onChange, options, placeholder = 'Choose…', required, error, hint, allowEmpty, disabled, name, onBlur },
  ref,
) {
  const id = useId()
  return (
    <FieldFrame id={id} label={label} required={required} hint={hint} error={error}>
      <Select.Root
        value={value ?? (allowEmpty ? NONE : '')}
        onValueChange={(next) => onChange(next === NONE ? null : next)}
        disabled={disabled}
        name={name}
      >
        <Select.Trigger
          ref={ref}
          id={id}
          onBlur={onBlur}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(id, hint, error)}
          className={controlClasses(
            Boolean(error),
            'flex min-h-11 items-center justify-between gap-2 py-2 text-left data-[placeholder]:text-ink-muted',
          )}
        >
          <Select.Value placeholder={placeholder} />
          <Select.Icon>
            <ChevronDownIcon width={16} height={16} className="text-ink-muted" />
          </Select.Icon>
        </Select.Trigger>
        <Select.Portal>
          <Select.Content
            position="popper"
            sideOffset={4}
            className="popover-enter z-50 max-h-[min(360px,var(--radix-select-content-available-height))] w-[var(--radix-select-trigger-width)] min-w-[220px] overflow-hidden rounded-card border border-line bg-surface shadow-[0_8px_24px_rgba(27,42,65,0.14)]"
          >
            <Select.Viewport className="p-1">
              {allowEmpty ? <Item value={NONE} label={allowEmpty} /> : null}
              {options.map((option) => (
                <Item key={option.value} value={option.value} label={option.label} />
              ))}
            </Select.Viewport>
          </Select.Content>
        </Select.Portal>
      </Select.Root>
    </FieldFrame>
  )
})

function Item({ value, label }: SelectOption) {
  return (
    <Select.Item
      value={value}
      className={cx(
        'relative flex min-h-10 cursor-pointer select-none items-center rounded-control py-2 pr-3 pl-8 text-sm text-ink outline-none',
        'data-[highlighted]:bg-tint-neutral data-[state=checked]:font-medium',
      )}
    >
      <Select.ItemIndicator className="absolute left-2 text-accent">
        <CheckIcon width={16} height={16} />
      </Select.ItemIndicator>
      <Select.ItemText>{label}</Select.ItemText>
    </Select.Item>
  )
}
