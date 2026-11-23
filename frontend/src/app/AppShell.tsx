import { useQueryClient } from '@tanstack/react-query'
import { Dialog, DropdownMenu, VisuallyHidden } from 'radix-ui'
import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router'

import { signOut, useMe } from '../api/auth'
import { cx } from '../components/ui/cx'
import { ChevronDownIcon, CloseIcon, MenuIcon } from '../components/ui/icons'
import { useToast } from '../components/ui/Toast'
import { errorMessage } from '../lib/errors'
import { Wordmark } from './Wordmark'

const NAV = [
  { to: '/app', label: 'Dashboard', end: true },
  { to: '/app/invoices', label: 'Invoices', end: false },
  { to: '/app/customers', label: 'Customers', end: false },
  { to: '/app/templates', label: 'Templates', end: false },
  { to: '/app/business', label: 'Business', end: false },
] as const

function navClasses({ isActive }: { isActive: boolean }) {
  return cx(
    'rounded-control px-3 py-2 text-sm font-medium transition-colors duration-150',
    isActive ? 'bg-tint-accent text-accent' : 'text-ink-muted hover:bg-tint-neutral hover:text-ink',
  )
}

/** On route change, focus moves to the page h1 (docs/08 §8). */
function useFocusHeadingOnNavigate() {
  const location = useLocation()
  const first = useRef(true)
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    const frame = window.requestAnimationFrame(() => {
      document.querySelector<HTMLElement>('#main h1')?.focus({ preventScroll: false })
    })
    return () => window.cancelAnimationFrame(frame)
  }, [location.pathname])
}

/** The signed-in layout (docs/08 §12.2): top bar, drawer below 768 px, footer. */
export function AppShell() {
  const me = useMe()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const toast = useToast()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)
  useFocusHeadingOnNavigate()

  const session = me.data
  async function handleSignOut() {
    setSigningOut(true)
    try {
      await signOut(queryClient)
      navigate('/login', { replace: true })
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setSigningOut(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <a
        href="#main"
        className="sr-only z-50 rounded-control bg-surface px-3 py-2 text-sm font-medium text-ink focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-line bg-surface/95 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-[1200px] items-center gap-3 px-4 md:px-6 lg:px-8">
          <Dialog.Root open={drawerOpen} onOpenChange={setDrawerOpen}>
            <Dialog.Trigger
              className="-ml-2 flex h-10 w-10 items-center justify-center rounded-control text-ink hover:bg-tint-neutral md:hidden"
              aria-label="Open navigation"
            >
              <MenuIcon />
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="overlay-enter fixed inset-0 z-40 bg-ink/40" />
              <Dialog.Content className="drawer-enter fixed inset-y-0 left-0 z-50 flex w-[min(320px,86vw)] flex-col bg-surface p-4 shadow-[0_8px_32px_rgba(27,42,65,0.2)] outline-none">
                <div className="mb-4 flex items-center justify-between">
                  <Dialog.Title asChild>
                    <span>
                      <Wordmark compact />
                    </span>
                  </Dialog.Title>
                  <VisuallyHidden.Root>
                    <Dialog.Description>Main navigation</Dialog.Description>
                  </VisuallyHidden.Root>
                  <Dialog.Close
                    className="flex h-10 w-10 items-center justify-center rounded-control text-ink hover:bg-tint-neutral"
                    aria-label="Close navigation"
                  >
                    <CloseIcon />
                  </Dialog.Close>
                </div>
                <nav aria-label="Main" className="flex flex-col gap-1">
                  {NAV.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.end}
                      onClick={() => setDrawerOpen(false)}
                      className={(state) => cx(navClasses(state), 'py-3 text-base')}
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </nav>
                <div className="mt-auto border-t border-line pt-4">
                  <p className="text-sm font-medium text-ink">{session?.user.display_name}</p>
                  <p className="text-xs text-ink-muted">{session?.organization.name}</p>
                  <button
                    type="button"
                    onClick={handleSignOut}
                    disabled={signingOut}
                    className="mt-3 min-h-10 w-full rounded-control border border-field-border text-sm font-medium text-ink hover:bg-paper disabled:opacity-60"
                  >
                    {signingOut ? 'Signing out…' : 'Sign out'}
                  </button>
                </div>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>

          <Link to="/app" className="rounded-control" aria-label="HIVE DOCS dashboard">
            <Wordmark compact />
          </Link>

          <nav aria-label="Main" className="ml-4 hidden items-center gap-1 md:flex">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end} className={navClasses}>
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto">
            <DropdownMenu.Root>
              <DropdownMenu.Trigger className="flex min-h-10 max-w-[220px] items-center gap-2 rounded-control px-2 text-sm text-ink hover:bg-tint-neutral">
                <span
                  aria-hidden="true"
                  className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ink text-xs font-semibold text-paper"
                >
                  {(session?.user.display_name ?? '?').slice(0, 1).toUpperCase()}
                </span>
                <span className="hidden truncate font-medium lg:inline">{session?.user.display_name}</span>
                <ChevronDownIcon width={16} height={16} className="text-ink-muted" />
                <span className="sr-only">Account menu</span>
              </DropdownMenu.Trigger>
              <DropdownMenu.Portal>
                <DropdownMenu.Content
                  align="end"
                  sideOffset={6}
                  className="popover-enter z-50 min-w-[240px] rounded-card border border-line bg-surface p-1.5 shadow-[0_8px_24px_rgba(27,42,65,0.14)]"
                >
                  <div className="px-2.5 py-2">
                    <p className="text-sm font-medium text-ink">{session?.user.display_name}</p>
                    <p className="text-xs text-ink-muted">{session?.organization.name}</p>
                    <p className="mt-0.5 truncate text-xs text-ink-muted">{session?.user.email}</p>
                  </div>
                  <DropdownMenu.Separator className="my-1 h-px bg-line" />
                  <DropdownMenu.Item
                    onSelect={handleSignOut}
                    disabled={signingOut}
                    className="flex min-h-10 cursor-pointer items-center rounded-control px-2.5 text-sm font-medium text-ink outline-none data-[highlighted]:bg-tint-neutral"
                  >
                    {signingOut ? 'Signing out…' : 'Sign out'}
                  </DropdownMenu.Item>
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
          </div>
        </div>
      </header>

      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-[1200px] flex-1 px-4 py-6 outline-none md:px-6 md:py-8 lg:px-8">
        <Outlet />
      </main>

      <footer className="border-t border-line">
        <p className="mx-auto max-w-[1200px] px-4 py-4 text-xs text-ink-muted md:px-6 lg:px-8">
          Demonstration build — PDFs are specimens, not tax invoices.
        </p>
      </footer>
    </div>
  )
}
