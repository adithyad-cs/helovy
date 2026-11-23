import { Link } from 'react-router'

import { useMe } from '../api/auth'
import { useDocumentTitle } from '../lib/useDocumentTitle'

/** docs/08 §22: links to the dashboard when signed in, otherwise home. */
export function NotFoundPage({ inShell = false }: { inShell?: boolean }) {
  const me = useMe()
  useDocumentTitle('Page not found')
  const signedIn = Boolean(me.data)
  const body = (
    <div className="flex flex-col gap-4">
      <h1 tabIndex={-1} className="font-serif text-2xl font-semibold text-ink outline-none md:text-[30px] md:leading-9">
        Page not found
      </h1>
      <p className="text-base text-ink-muted">The page you&apos;re looking for doesn&apos;t exist.</p>
      <p>
        <Link className="font-medium text-accent underline underline-offset-2 hover:text-accent-hover" to={signedIn ? '/app' : '/'}>
          {signedIn ? 'Dashboard' : 'Home'}
        </Link>
      </p>
    </div>
  )
  if (inShell) return body
  return (
    <main id="main" className="mx-auto flex min-h-screen max-w-[1200px] flex-col justify-center px-4 md:px-6 lg:px-8">
      {body}
    </main>
  )
}
