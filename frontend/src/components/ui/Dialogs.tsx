import { AlertDialog } from 'radix-ui'
import type { ReactNode } from 'react'

import { Button } from './Button'

interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  children?: ReactNode
  confirmLabel: string
  cancelLabel?: string
  onConfirm: () => void
  tone?: 'primary' | 'danger'
  busy?: boolean
  busyLabel?: string
}

/** Irreversible or disruptive actions ask first, in plain language (docs/08 §1). */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  children,
  confirmLabel,
  cancelLabel = 'Cancel',
  onConfirm,
  tone = 'primary',
  busy = false,
  busyLabel,
}: ConfirmDialogProps) {
  return (
    <AlertDialog.Root open={open} onOpenChange={(next) => (busy ? undefined : onOpenChange(next))}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="overlay-enter fixed inset-0 z-40 bg-ink/40" />
        <AlertDialog.Content className="dialog-enter fixed top-1/2 left-1/2 z-50 w-[calc(100vw-32px)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-card bg-surface p-6 shadow-[0_16px_48px_rgba(27,42,65,0.22)] outline-none">
          <AlertDialog.Title className="font-serif text-xl font-semibold text-ink">{title}</AlertDialog.Title>
          <AlertDialog.Description asChild>
            <div className="mt-3 text-sm text-ink">{children}</div>
          </AlertDialog.Description>
          <div className="mt-6 flex flex-col-reverse gap-2 md:flex-row md:justify-end">
            <AlertDialog.Cancel asChild>
              <Button variant="secondary" disabled={busy}>
                {cancelLabel}
              </Button>
            </AlertDialog.Cancel>
            <Button
              variant={tone === 'danger' ? 'danger' : 'primary'}
              onClick={onConfirm}
              loading={busy}
              loadingText={busyLabel}
            >
              {confirmLabel}
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  )
}

/** 412 `version_mismatch` (docs/08 §9). */
export function ConflictDialog({ open, onReload }: { open: boolean; onReload: () => void }) {
  return (
    <ConfirmDialog
      open={open}
      onOpenChange={() => undefined}
      title="This was changed elsewhere"
      confirmLabel="Reload"
      cancelLabel="Keep editing"
      onConfirm={onReload}
    >
      This was changed elsewhere. Reload to see the latest version.
    </ConfirmDialog>
  )
}
