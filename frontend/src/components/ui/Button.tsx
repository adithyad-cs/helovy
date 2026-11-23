import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { Link, type LinkProps } from 'react-router'

import { cx } from './cx'
import { Spinner } from './Spinner'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'danger-ghost'
export type ButtonSize = 'md' | 'lg'

const BASE =
  'inline-flex select-none items-center justify-center gap-2 rounded-control font-medium ' +
  'transition-[background-color,color,box-shadow,transform] duration-150 ease-out ' +
  'active:translate-y-px disabled:cursor-not-allowed disabled:opacity-55 disabled:active:translate-y-0'

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-white shadow-[0_1px_0_rgba(27,42,65,0.12)] hover:bg-accent-hover',
  secondary: 'border border-field-border bg-surface text-ink hover:bg-paper',
  ghost: 'text-ink hover:bg-tint-neutral',
  danger: 'bg-danger text-white hover:brightness-95',
  'danger-ghost': 'text-danger hover:bg-tint-danger',
}

const SIZES: Record<ButtonSize, string> = {
  md: 'min-h-10 px-4 text-sm',
  lg: 'min-h-12 px-6 text-base',
}

export function buttonClasses(variant: ButtonVariant = 'primary', size: ButtonSize = 'md', extra?: string) {
  return cx(BASE, VARIANTS[variant], SIZES[size], extra)
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  loadingText?: ReactNode
}

/** docs/08 §2: at least 40 px tall; disabled with a spinner while its request is in flight. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading = false, loadingText, className, children, disabled, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? 'button'}
      className={buttonClasses(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner /> : null}
      {loading && loadingText ? loadingText : children}
    </button>
  )
})

interface ButtonLinkProps extends LinkProps {
  variant?: ButtonVariant
  size?: ButtonSize
}

export function ButtonLink({ variant = 'primary', size = 'md', className, ...rest }: ButtonLinkProps) {
  return <Link className={buttonClasses(variant, size, typeof className === 'string' ? className : undefined)} {...rest} />
}
