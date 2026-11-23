import { PageHeader } from '../components/ui/PageHeader'
import { useDocumentTitle } from '../lib/useDocumentTitle'

/** An honest placeholder for a section that a later build step adds (never fake content). */
export function NotBuiltYetPage({ title }: { title: string }) {
  useDocumentTitle(title)
  return (
    <>
      <PageHeader title={title} />
      <p className="max-w-prose text-base text-ink-muted">This page is not available in this build yet.</p>
    </>
  )
}
