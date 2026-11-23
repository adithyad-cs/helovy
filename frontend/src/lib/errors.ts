/** User-facing error copy (docs/08 §21). Clients branch on `code`, never on titles. */
import { ApiError, NetworkError } from '../api/http'

export const OFFLINE_MESSAGE = "Can't reach HIVE DOCS. Check your connection or that the app is running."

const COPY: Record<string, string> = {
  invalid_credentials: 'Email or password is incorrect.',
  unauthenticated: 'Your session ended. Please sign in again.',
  csrf_failed: 'Your session needs refreshing. Please try again.',
  not_found: "This item doesn't exist or you don't have access to it.",
  business_already_exists: 'Your business is already set up. Opening your profile.',
  version_mismatch: 'This was changed elsewhere. Reload to see the latest version.',
  document_not_draft: "This invoice has already been finalised and can't be changed.",
  document_not_finalized: 'Finalise this invoice before downloading its PDF.',
  pdf_not_ready: "The PDF isn't ready yet.",
  pdf_render_in_progress: 'The PDF is still being generated.',
  number_series_exhausted: 'No more invoice numbers are available for this financial year. Contact support.',
  idempotency_in_progress: 'Still confirming your previous request…',
  validation_failed: 'Please correct the highlighted fields.',
  payload_too_large: 'This request is too large. Remove some lines or text.',
  dependency_unavailable: 'The service is temporarily unavailable. Try again shortly.',
}

export function minutesFrom(seconds: number | null): number {
  return Math.max(1, Math.ceil((seconds ?? 60) / 60))
}

/** The message for any error, with the request ID where docs/08 §21 asks for it. */
export function errorMessage(error: unknown): string {
  if (error instanceof NetworkError) return OFFLINE_MESSAGE
  if (!(error instanceof ApiError)) return 'Something went wrong.'
  if (error.code === 'rate_limited') {
    const minutes = minutesFrom(error.retryAfterSeconds)
    return `Too many attempts. Try again in ${minutes} minute${minutes === 1 ? '' : 's'}.`
  }
  if (error.code === 'integrity_check_failed') {
    return `This PDF failed its integrity check and was not downloaded. Reference: ${error.requestId ?? 'unknown'}.`
  }
  const known = COPY[error.code]
  if (known) return known
  return `Something went wrong. Reference: ${error.requestId ?? 'unknown'}.`
}

export function requestIdOf(error: unknown): string | null {
  return error instanceof ApiError ? error.requestId : null
}
