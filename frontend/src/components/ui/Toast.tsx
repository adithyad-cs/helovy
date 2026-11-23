import { Toast as RadixToast } from 'radix-ui'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

import { cx } from './cx'

type Tone = 'success' | 'error'

interface ToastItem {
  id: number
  title: string
  tone: Tone
}

interface ToastApi {
  success: (title: string) => void
  error: (title: string) => void
}

const ToastContext = createContext<ToastApi | null>(null)

/** Success toasts last 4 s; errors stay until dismissed (docs/08 §2). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const push = useCallback((title: string, tone: Tone) => {
    setItems((current) => [...current.slice(-2), { id: Date.now() + Math.random(), title, tone }])
  }, [])
  const api = useMemo<ToastApi>(
    () => ({ success: (title) => push(title, 'success'), error: (title) => push(title, 'error') }),
    [push],
  )
  const remove = (id: number) => setItems((current) => current.filter((item) => item.id !== id))

  return (
    <ToastContext.Provider value={api}>
      <RadixToast.Provider swipeDirection="right" label="Notifications">
        {children}
        {items.map((item) => (
          <RadixToast.Root
            key={item.id}
            duration={item.tone === 'success' ? 4000 : Infinity}
            type={item.tone === 'error' ? 'foreground' : 'background'}
            onOpenChange={(open) => {
              if (!open) remove(item.id)
            }}
            className={cx(
              'toast-enter flex items-start gap-3 rounded-card border bg-surface px-4 py-3 text-sm text-ink shadow-[0_8px_24px_rgba(27,42,65,0.14)]',
              item.tone === 'success' ? 'border-accent/40' : 'border-danger/40',
            )}
          >
            <span
              aria-hidden="true"
              className={cx(
                'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white',
                item.tone === 'success' ? 'bg-accent' : 'bg-danger',
              )}
            >
              {item.tone === 'success' ? '✓' : '!'}
            </span>
            <RadixToast.Title className="flex-1 font-medium">{item.title}</RadixToast.Title>
            <RadixToast.Close aria-label="Dismiss" className="rounded-control px-1 text-ink-muted hover:text-ink">
              ×
            </RadixToast.Close>
          </RadixToast.Root>
        ))}
        <RadixToast.Viewport className="fixed right-0 bottom-0 z-50 m-0 flex w-full max-w-sm list-none flex-col gap-2 p-4 outline-none" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const api = useContext(ToastContext)
  if (!api) throw new Error('useToast needs <ToastProvider>')
  return api
}
