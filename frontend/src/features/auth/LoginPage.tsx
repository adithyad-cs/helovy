import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import { z } from 'zod'

import { clearSessionEnded, signIn, useMe } from '../../api/auth'
import { ApiError } from '../../api/http'
import { queryKeys } from '../../api/queryKeys'
import { Banner } from '../../components/ui/Banner'
import { Button } from '../../components/ui/Button'
import { TextField } from '../../components/ui/Field'
import { EyeIcon, EyeOffIcon } from '../../components/ui/icons'
import { Spinner } from '../../components/ui/Spinner'
import { errorMessage } from '../../lib/errors'
import { safeNext } from '../../lib/navigation'
import { Wordmark } from '../../app/Wordmark'

const schema = z.object({
  email: z.string().trim().min(1, 'Enter your email address.').max(254, 'Use at most 254 characters.'),
  password: z.string().min(1, 'Enter your password.').max(1024, 'Use at most 1,024 characters.'),
})

type FormValues = z.infer<typeof schema>

/** /login (docs/08 §11): no sign-up and no "forgot password" (P1-01). */
export function LoginPage() {
  const me = useMe()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showPassword, setShowPassword] = useState(false)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const next = safeNext(params.get('next'))
  const expired = params.get('reason') === 'expired'

  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '' } })
  const mutation = useMutation({
    mutationFn: (values: FormValues) => signIn(values.email, values.password),
    onSuccess: (session) => {
      clearSessionEnded()
      queryClient.setQueryData(queryKeys.me, session)
      navigate(next, { replace: true })
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === 'validation_failed') {
        for (const field of error.fieldErrors) {
          const name = field.pointer.replace(/^\//, '')
          if (name === 'email' || name === 'password') form.setError(name, { message: field.message })
        }
      }
      form.setFocus('password')
    },
  })

  useEffect(() => {
    document.title = 'Sign in · HIVE DOCS'
  }, [])

  if (me.data) return <Navigate to={next} replace />

  const submitting = mutation.isPending
  const failure = mutation.error && !(mutation.error instanceof ApiError && mutation.error.code === 'validation_failed')

  return (
    <main id="main" className="flex min-h-screen flex-col items-center justify-center bg-paper px-4 py-10">
      <div className="w-full max-w-[420px]">
        <div className="mb-6 flex justify-center">
          <Link to="/" className="rounded-control">
            <Wordmark />
          </Link>
        </div>
        <section className="card-enter rounded-card border border-line bg-surface p-6 shadow-[0_1px_2px_rgba(27,42,65,0.06)] md:p-8">
          <h1 ref={headingRef} tabIndex={-1} className="font-serif text-2xl font-semibold text-ink outline-none md:text-[30px] md:leading-9">
            Sign in
          </h1>
          <p className="mt-2 text-sm text-ink-muted">
            This is a demonstration workspace. Accounts are created by the administrator.
          </p>

          <div className="mt-5 flex flex-col gap-3" aria-live="polite">
            {expired && !failure ? <Banner tone="info">Your session ended. Please sign in again.</Banner> : null}
            {failure ? <Banner tone="danger">{errorMessage(mutation.error)}</Banner> : null}
          </div>

          <form
            className="mt-5 flex flex-col gap-4"
            noValidate
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          >
            <fieldset disabled={submitting} className="flex flex-col gap-4">
              <TextField
                label="Email"
                type="email"
                autoComplete="username"
                inputMode="email"
                spellCheck={false}
                required
                error={form.formState.errors.email?.message}
                {...form.register('email')}
              />
              <TextField
                label="Password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                required
                error={form.formState.errors.password?.message}
                trailing={
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    aria-pressed={showPassword}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="flex min-h-9 items-center gap-1 rounded-control px-2 text-sm text-ink-muted hover:bg-tint-neutral hover:text-ink"
                  >
                    {showPassword ? <EyeOffIcon width={18} height={18} /> : <EyeIcon width={18} height={18} />}
                    <span>{showPassword ? 'Hide' : 'Show'}</span>
                  </button>
                }
                {...form.register('password')}
              />
            </fieldset>
            <Button type="submit" size="lg" loading={submitting} loadingText="Signing in…" className="mt-1 w-full">
              Sign in
            </Button>
          </form>
        </section>
        <p className="mt-6 text-center text-xs text-ink-muted">
          Demonstration build — PDFs are specimens, not tax invoices.
        </p>
        {me.isPending ? (
          <p className="sr-only" role="status">
            <Spinner /> Checking your session…
          </p>
        ) : null}
      </div>
    </main>
  )
}
