import { Link } from 'react-router'

/** docs/08 §22. The Dashboard link for signed-in users arrives with sessions in M1. */
export function NotFoundPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-[1200px] flex-col justify-center gap-4 px-4 md:px-6 lg:px-8">
      <h1 className="font-serif text-3xl font-semibold text-ink">Page not found</h1>
      <p className="text-base text-ink-muted">The page you&apos;re looking for doesn&apos;t exist.</p>
      <p>
        <Link className="font-medium text-accent underline hover:text-accent-hover" to="/">
          Home
        </Link>
      </p>
    </main>
  )
}
