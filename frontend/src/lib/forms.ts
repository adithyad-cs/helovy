/** Form helpers: server field errors onto React Hook Form fields (docs/04 §4; docs/08 §8). */
import type { FieldValues, Path, UseFormReturn } from 'react-hook-form'

import { ApiError } from '../api/http'

/** Applies `errors[].pointer` values such as `/legal_name` to fields; returns those not placed. */
export function applyServerErrors<T extends FieldValues>(
  form: UseFormReturn<T>,
  error: unknown,
  fields: ReadonlyArray<string>,
): string[] {
  if (!(error instanceof ApiError) || error.code !== 'validation_failed') return []
  const unplaced: string[] = []
  let first: string | null = null
  for (const item of error.fieldErrors) {
    const name = item.pointer.replace(/^\//, '').split('/')[0] ?? ''
    if (fields.includes(name)) {
      form.setError(name as Path<T>, { type: 'server', message: item.message })
      first ??= name
    } else {
      unplaced.push(item.message)
    }
  }
  if (first) form.setFocus(first as Path<T>)
  return unplaced
}

/** Text input → API value: trimmed; empty optional text is sent as null (docs/09 §4.2). */
export function optional(value: string | null | undefined): string | null {
  const trimmed = (value ?? '').trim()
  return trimmed === '' ? null : trimmed
}

/** Only the fields whose values differ from the loaded record (PATCH semantics, docs/07 §1.4). */
export function changedFields<T extends object>(next: T, current: object): Partial<T> {
  const changes: Partial<T> = {}
  const before = current as Record<string, unknown>
  for (const key of Object.keys(next) as Array<keyof T>) {
    if ((next[key] ?? null) !== (before[key as string] ?? null)) changes[key] = next[key]
  }
  return changes
}
