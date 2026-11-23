import { Dialog } from 'radix-ui'
import { useEffect, useState } from 'react'

import { previewPdf } from '../../api/documents'
import { ApiError } from '../../api/http'
import { Banner } from '../../components/ui/Banner'
import { Button, buttonClasses } from '../../components/ui/Button'
import { CloseIcon, DownloadIcon } from '../../components/ui/icons'
import { Spinner } from '../../components/ui/Spinner'
import { errorMessage } from '../../lib/errors'
import { useMediaQuery } from '../../lib/useMediaQuery'

function previewError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'validation_failed' && error.fieldErrors.some((e) => e.code === 'no_lines')) return 'Add at least one line to preview.'
    if (error.code === 'rate_limited') return 'Please wait a moment before previewing again.'
    if (error.code === 'dependency_unavailable') return 'The PDF service is busy. Try again.'
  }
  return errorMessage(error)
}

type State = { status: 'idle' } | { status: 'loading' } | { status: 'ready'; url: string } | { status: 'error'; error: unknown }

/** The watermarked draft preview (docs/08 §17): fetched as a blob, never stored. */
export function PreviewButton({ documentId, disabled, beforeOpen }: { documentId: string; disabled: boolean; beforeOpen: () => Promise<boolean> }) {
  const [state, setState] = useState<State>({ status: 'idle' })
  const [open, setOpen] = useState(false)
  const wide = useMediaQuery('(min-width: 48rem)')

  useEffect(() => {
    if (state.status !== 'ready') return
    const url = state.url
    return () => URL.revokeObjectURL(url)
  }, [state])

  async function start() {
    setState({ status: 'loading' })
    const saved = await beforeOpen()
    if (!saved) {
      setState({ status: 'idle' })
      return
    }
    setOpen(true)
    try {
      const blob = await previewPdf(documentId)
      setState({ status: 'ready', url: URL.createObjectURL(blob) })
    } catch (error) {
      setState({ status: 'error', error })
    }
  }

  function close(next: boolean) {
    setOpen(next)
    if (!next) setState({ status: 'idle' })
  }

  return (
    <>
      <Button variant="secondary" className="w-full" disabled={disabled} loading={state.status === 'loading'} loadingText="Generating preview…" onClick={() => void start()}>
        Preview PDF
      </Button>
      <Dialog.Root open={open} onOpenChange={close}>
        <Dialog.Portal>
          <Dialog.Overlay className="overlay-enter fixed inset-0 z-40 bg-ink/50" />
          <Dialog.Content className="dialog-enter fixed top-1/2 left-1/2 z-50 flex max-h-[calc(100vh-32px)] w-[calc(100vw-32px)] max-w-5xl -translate-x-1/2 -translate-y-1/2 flex-col rounded-card bg-surface shadow-[0_16px_48px_rgba(27,42,65,0.25)] outline-none md:h-[calc(100vh-48px)]">
            <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3 md:px-6">
              <div>
                <Dialog.Title className="font-serif text-xl font-semibold text-ink">Draft preview</Dialog.Title>
                <Dialog.Description className="text-xs text-ink-muted">Watermarked and not stored. The number and date are assigned when you finalise.</Dialog.Description>
              </div>
              <div className="flex items-center gap-2">
                {state.status === 'ready' ? (
                  <a href={state.url} download="draft-preview.pdf" className={buttonClasses('secondary', 'md')}>
                    <DownloadIcon width={18} height={18} /> Download preview
                  </a>
                ) : null}
                <Dialog.Close className="flex h-10 w-10 items-center justify-center rounded-control text-ink hover:bg-tint-neutral" aria-label="Close preview">
                  <CloseIcon />
                </Dialog.Close>
              </div>
            </div>
            <div className="min-h-0 flex-1 p-3 md:p-4">
              {state.status === 'ready' ? (
                wide ? (
                  <iframe title="Draft preview PDF" src={state.url} className="h-full min-h-[60vh] w-full rounded-control border border-line bg-paper" />
                ) : (
                  <div className="flex flex-col items-start gap-3 p-2">
                    <p className="text-sm text-ink">The preview is ready.</p>
                    <a href={state.url} target="_blank" rel="noopener" className={buttonClasses('primary', 'lg')}>
                      Open preview
                    </a>
                  </div>
                )
              ) : state.status === 'error' ? (
                <div className="p-2">
                  <Banner tone="danger" action={<Button variant="secondary" onClick={() => void start()}>Try again</Button>}>
                    {previewError(state.error)}
                  </Banner>
                </div>
              ) : (
                <p role="status" className="flex h-full min-h-40 items-center justify-center gap-2 text-sm text-ink-muted">
                  <Spinner /> Generating preview…
                </p>
              )}
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  )
}
