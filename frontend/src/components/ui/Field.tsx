import { forwardRef, useId, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from 'react'

import { cx } from './cx'

const CONTROL =
  'block w-full rounded-control border bg-surface px-3 text-base text-ink placeholder:text-ink-muted/70 ' +
  'transition-[border-color,box-shadow] duration-150 ease-out ' +
  'focus:border-focus focus:outline-none focus:ring-2 focus:ring-focus/25 ' +
  'disabled:cursor-not-allowed disabled:bg-paper disabled:text-ink-muted md:text-sm'

export function controlClasses(invalid: boolean, extra?: string) {
  return cx(CONTROL, invalid ? 'border-danger' : 'border-field-border', extra)
}

interface FieldFrameProps {
  id: string
  label: ReactNode
  required?: boolean
  hint?: ReactNode
  error?: string
  counter?: ReactNode
  children: ReactNode
  className?: string
}

/** A visible label, "(required)" in text, hint and error linked by aria-describedby (docs/08 §8). */
export function FieldFrame({ id, label, required, hint, error, counter, children, className }: FieldFrameProps) {
  return (
    <div className={cx('flex flex-col gap-1.5', className)}>
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {label}
          {required ? <span className="font-normal text-ink-muted"> (required)</span> : null}
        </label>
        {counter ? <span className="text-xs tabular-nums text-ink-muted">{counter}</span> : null}
      </div>
      {children}
      {hint && !error ? (
        <p id={`${id}-hint`} className="text-xs text-ink-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} className="flex items-start gap-1 text-sm text-danger">
          <span aria-hidden="true">!</span>
          <span>{error}</span>
        </p>
      ) : null}
    </div>
  )
}

export function describedBy(id: string, hint: unknown, error: unknown): string | undefined {
  if (error) return `${id}-error`
  if (hint) return `${id}-hint`
  return undefined
}

interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> {
  label: ReactNode
  hint?: ReactNode
  error?: string
  required?: boolean
  id?: string
  frameClassName?: string
  trailing?: ReactNode
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(function TextField(
  { label, hint, error, required, id, frameClassName, className, trailing, ...rest },
  ref,
) {
  const generated = useId()
  const inputId = id ?? generated
  return (
    <FieldFrame id={inputId} label={label} required={required} hint={hint} error={error} className={frameClassName}>
      <div className="relative">
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(inputId, hint, error)}
          aria-required={required || undefined}
          className={controlClasses(Boolean(error), cx('min-h-11 py-2', trailing ? 'pr-20' : undefined, className))}
          {...rest}
        />
        {trailing ? <div className="absolute inset-y-0 right-1 flex items-center">{trailing}</div> : null}
      </div>
    </FieldFrame>
  )
})

interface TextAreaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id'> {
  label: ReactNode
  hint?: ReactNode
  error?: string
  maxChars: number
  currentLength: number
  id?: string
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea(
  { label, hint, error, maxChars, currentLength, id, className, ...rest },
  ref,
) {
  const generated = useId()
  const areaId = id ?? generated
  return (
    <FieldFrame
      id={areaId}
      label={label}
      hint={hint}
      error={error}
      counter={`${currentLength.toLocaleString('en-IN')} / ${maxChars.toLocaleString('en-IN')}`}
    >
      <textarea
        ref={ref}
        id={areaId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(areaId, hint, error)}
        className={controlClasses(Boolean(error), cx('min-h-24 py-2', className))}
        {...rest}
      />
    </FieldFrame>
  )
})
