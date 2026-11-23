/**
 * Placeholder for the foundation build (M0). It states plainly that the product screens are
 * not built yet; it is replaced by the landing page in M7 (docs/08 §10).
 */
export function SkeletonPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-[1200px] flex-col justify-center gap-4 px-4 md:px-6 lg:px-8">
      <p className="w-fit rounded-control bg-tint-neutral px-2 py-1 text-xs font-medium text-ink-muted">
        Demonstration build
      </p>
      <h1 className="font-serif text-3xl font-semibold text-ink">HIVE DOCS</h1>
      <p className="max-w-prose text-base text-ink-muted">
        This build contains the application foundation only. Sign-in and the invoice workflow
        are not available yet.
      </p>
    </main>
  )
}
