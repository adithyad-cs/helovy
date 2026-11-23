import { Link } from 'react-router'

/**
 * Placeholder for the public landing page, which is built in M7 (docs/08 §10). It states
 * plainly that the landing page is not built yet and links to the real sign-in page.
 */
export function SkeletonPage() {
  return (
    <main id="main" className="mx-auto flex min-h-screen max-w-[1200px] flex-col justify-center gap-4 px-4 md:px-6 lg:px-8">
      <p className="w-fit rounded-control bg-tint-neutral px-2 py-1 text-xs font-medium text-ink-muted">
        Demonstration build
      </p>
      <h1 className="font-serif text-3xl font-semibold text-ink">HIVE DOCS</h1>
      <p className="max-w-prose text-base text-ink-muted">The landing page is not built yet in this build.</p>
      <p>
        <Link className="font-medium text-accent underline underline-offset-2 hover:text-accent-hover" to="/login">
          Sign in
        </Link>
      </p>
    </main>
  )
}
