import type { Blocker } from 'react-router'

import { ConfirmDialog } from './Dialogs'

export function LeaveGuardDialog({ blocker }: { blocker: Blocker }) {
  return (
    <ConfirmDialog
      open={blocker.state === 'blocked'}
      onOpenChange={(open) => {
        if (!open && blocker.state === 'blocked') blocker.reset()
      }}
      title="Leave without saving?"
      confirmLabel="Leave page"
      cancelLabel="Stay"
      tone="danger"
      onConfirm={() => blocker.state === 'blocked' && blocker.proceed()}
    >
      You have unsaved changes. If you leave this page, they will be lost.
    </ConfirmDialog>
  )
}
