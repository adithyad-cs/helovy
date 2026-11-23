import { useTemplates } from '../../api/documents'
import { PageHeader } from '../../components/ui/PageHeader'
import { DelayedSkeleton, Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/ui/States'
import { useDocumentTitle } from '../../lib/useDocumentTitle'

/** A CSS-drawn miniature of the Classic layout (not an image; docs/08 §16). */
function ClassicMiniature() {
  return (
    <div aria-hidden="true" className="mx-auto aspect-[210/297] w-40 rounded-[4px] border border-line bg-surface p-3 shadow-[0_2px_8px_rgba(27,42,65,0.08)]">
      <div className="flex justify-between">
        <div className="space-y-1">
          <div className="h-1.5 w-14 rounded bg-ink" />
          <div className="h-1 w-10 rounded bg-line" />
          <div className="h-1 w-12 rounded bg-line" />
        </div>
        <div className="space-y-1 text-right">
          <div className="ml-auto h-2 w-9 rounded bg-ink" />
          <div className="ml-auto h-1 w-11 rounded bg-line" />
        </div>
      </div>
      <div className="mt-2 h-px w-full bg-accent" />
      <div className="mt-2 h-1 w-12 rounded bg-ink-muted/60" />
      <div className="mt-2 space-y-1.5">
        {[0, 1, 2, 3].map((row) => (
          <div key={row} className="flex justify-between border-b border-line pb-1">
            <div className="h-1 w-16 rounded bg-line" />
            <div className="h-1 w-6 rounded bg-line" />
          </div>
        ))}
      </div>
      <div className="mt-2 ml-auto w-14 space-y-1">
        <div className="h-1 w-full rounded bg-line" />
        <div className="h-1.5 w-full rounded bg-ink" />
      </div>
    </div>
  )
}

/** /app/templates (docs/08 §16): informational; Classic is the default for new drafts. */
export function TemplatesPage() {
  useDocumentTitle('Templates')
  const templates = useTemplates()
  return (
    <>
      <PageHeader title="Templates" description="Classic is used for new invoices. Every PDF carries the specimen notice." />
      {templates.isPending ? (
        <DelayedSkeleton label="Loading templates…">
          <Skeleton className="h-72 w-full max-w-sm" />
        </DelayedSkeleton>
      ) : templates.isError ? (
        <ErrorState error={templates.error} onRetry={() => void templates.refetch()} />
      ) : templates.data.length === 0 ? (
        <ErrorState error={null} title="No templates are available." />
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {templates.data.map((template) => (
            <li key={template.id} className="card-enter rounded-card border border-line bg-surface p-5">
              <div className="rounded-control bg-paper py-5">
                <ClassicMiniature />
              </div>
              <div className="mt-4 flex items-center gap-2">
                <h2 className="text-xl font-semibold text-ink">{template.name}</h2>
                <span className="rounded-full bg-tint-accent px-2 py-0.5 text-xs font-semibold text-accent">Free</span>
              </div>
              <p className="mt-1 text-sm text-ink-muted">{template.description}</p>
              <p className="mt-3 text-xs text-ink-muted">A4 · Noto Sans · Indian digit grouping · version {template.version}</p>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
