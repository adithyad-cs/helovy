import { useQuery } from '@tanstack/react-query'
import { Popover } from 'radix-ui'
import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'

import { listCustomers, type CustomerSummary } from '../../api/customers'
import { queryKeys } from '../../api/queryKeys'
import { controlClasses, FieldFrame } from '../../components/ui/Field'
import { ChevronDownIcon, SearchIcon } from '../../components/ui/icons'
import { Spinner } from '../../components/ui/Spinner'
import { errorMessage } from '../../lib/errors'

interface CustomerPickerProps {
  businessId: string
  value: { id: string; display_name: string } | null
  onChange: (customer: CustomerSummary) => void
  label?: string
  error?: string
  disabled?: boolean
  placeholder?: string
}

/** Radix Popover + listbox driven by E-09 search (docs/08 §2 CustomerPicker). */
export function CustomerPicker({ businessId, value, onChange, label = 'Customer', error, disabled, placeholder = 'Choose a customer' }: CustomerPickerProps) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [q, setQ] = useState('')
  const listRef = useRef<HTMLUListElement>(null)

  useEffect(() => {
    const timer = window.setTimeout(() => setQ(search.trim()), 250)
    return () => window.clearTimeout(timer)
  }, [search])

  const results = useQuery({
    queryKey: queryKeys.customers(businessId, { q, limit: 20, picker: true }),
    queryFn: () => listCustomers(businessId, { q, limit: 20 }),
    enabled: open,
  })

  function moveFocus(event: KeyboardEvent<HTMLElement>, from: number) {
    const options = Array.from(listRef.current?.querySelectorAll<HTMLButtonElement>('[role="option"]') ?? [])
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      options[Math.min(from + 1, options.length - 1)]?.focus()
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      if (from <= 0) document.getElementById(`${id}-search`)?.focus()
      else options[from - 1]?.focus()
    }
  }

  return (
    <FieldFrame id={id} label={label} required error={error}>
      <Popover.Root open={open} onOpenChange={setOpen}>
        <Popover.Trigger
          id={id}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          className={controlClasses(Boolean(error), 'flex min-h-11 items-center justify-between gap-2 py-2 text-left')}
        >
          <span className={value ? 'truncate text-ink' : 'text-ink-muted'}>{value?.display_name ?? placeholder}</span>
          <ChevronDownIcon width={16} height={16} className="shrink-0 text-ink-muted" />
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            sideOffset={4}
            className="popover-enter z-50 w-[var(--radix-popover-trigger-width)] min-w-[280px] rounded-card border border-line bg-surface p-2 shadow-[0_8px_24px_rgba(27,42,65,0.14)]"
          >
            <div className="relative">
              <SearchIcon width={16} height={16} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-muted" />
              <input
                id={`${id}-search`}
                autoFocus
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                onKeyDown={(event) => moveFocus(event, -1)}
                placeholder="Search by name"
                aria-label="Search customers by name"
                aria-controls={`${id}-list`}
                autoComplete="off"
                className={controlClasses(false, 'min-h-10 py-2 pl-9')}
              />
            </div>
            <ul id={`${id}-list`} ref={listRef} role="listbox" aria-label="Customers" className="mt-2 max-h-64 overflow-y-auto">
              {results.isPending ? (
                <li className="flex items-center gap-2 px-3 py-3 text-sm text-ink-muted">
                  <Spinner /> Searching…
                </li>
              ) : results.isError ? (
                <li className="px-3 py-3 text-sm text-danger">{errorMessage(results.error)}</li>
              ) : results.data.items.length === 0 ? (
                <li className="px-3 py-3 text-sm text-ink-muted">{q ? `No customers start with “${q}”.` : 'No customers yet.'}</li>
              ) : (
                results.data.items.map((customer, index) => (
                  <li key={customer.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={customer.id === value?.id}
                      onKeyDown={(event) => moveFocus(event, index)}
                      onClick={() => {
                        onChange(customer)
                        setOpen(false)
                        setSearch('')
                      }}
                      className="flex w-full min-h-10 flex-col items-start rounded-control px-3 py-2 text-left text-sm outline-none hover:bg-tint-neutral focus-visible:bg-tint-neutral aria-selected:font-semibold"
                    >
                      <span className="text-ink">{customer.display_name}</span>
                      {customer.city || customer.email ? (
                        <span className="text-xs text-ink-muted">{[customer.city, customer.email].filter(Boolean).join(' · ')}</span>
                      ) : null}
                    </button>
                  </li>
                ))
              )}
            </ul>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </FieldFrame>
  )
}
