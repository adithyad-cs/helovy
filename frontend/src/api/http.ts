/**
 * The API client (docs/04 §4): same-origin fetch, JSON in and out, RFC 9457 problems.
 *
 * - `credentials: 'same-origin'` sends the HttpOnly session cookie; the SPA never sees it.
 * - Unsafe methods carry `X-CSRF-Token`, held in memory only (never in browser storage).
 * - `If-Match` carries the ETag of the cached resource for PATCH, DELETE and finalise.
 * - Errors become `ApiError` (a problem response) or `NetworkError` (no response).
 */

export interface FieldError {
  pointer: string
  code: string
  message: string
}

export interface Problem {
  type: string
  title: string
  status: number
  detail: string
  instance?: string
  code: string
  request_id: string | null
  errors?: FieldError[]
  [extra: string]: unknown
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null
  readonly fieldErrors: FieldError[]
  readonly retryAfterSeconds: number | null
  readonly problem: Problem

  constructor(problem: Problem, retryAfterSeconds: number | null) {
    super(problem.detail || problem.title)
    this.name = 'ApiError'
    this.status = problem.status
    this.code = problem.code
    this.requestId = problem.request_id
    this.fieldErrors = problem.errors ?? []
    this.retryAfterSeconds = retryAfterSeconds
    this.problem = problem
  }
}

export class NetworkError extends Error {
  constructor() {
    super("Can't reach HIVE DOCS.")
    this.name = 'NetworkError'
  }
}

const UNSAFE = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

let csrfToken: string | null = null

/** Kept in memory only (docs/12 §4.2): set from E-03 and E-05 responses. */
export function setCsrfToken(token: string | null): void {
  csrfToken = token
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  ifMatch?: string | null
  idempotencyKey?: string
  signal?: AbortSignal
}

export interface ApiResponse<T> {
  data: T
  etag: string | null
  status: number
  headers: Headers
}

function buildHeaders(method: string, options: RequestOptions, accept: string): Headers {
  const headers = new Headers({ Accept: accept })
  if (options.body !== undefined) headers.set('Content-Type', 'application/json')
  if (UNSAFE.has(method) && csrfToken) headers.set('X-CSRF-Token', csrfToken)
  if (options.ifMatch) headers.set('If-Match', options.ifMatch)
  if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey)
  return headers
}

async function send(path: string, options: RequestOptions, accept: string): Promise<Response> {
  const method = options.method ?? 'GET'
  try {
    return await fetch(path, {
      method,
      credentials: 'same-origin',
      headers: buildHeaders(method, options, accept),
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new NetworkError()
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  const retryAfter = Number.parseInt(response.headers.get('Retry-After') ?? '', 10)
  let problem: Problem
  try {
    problem = (await response.json()) as Problem
  } catch {
    problem = {
      type: 'about:blank',
      title: response.statusText,
      status: response.status,
      detail: response.statusText,
      code: response.status >= 500 ? 'internal_error' : 'malformed_request',
      request_id: response.headers.get('X-Request-ID'),
    }
  }
  return new ApiError(problem, Number.isFinite(retryAfter) ? retryAfter : null)
}

/** A JSON request. A 204 response gives `data: undefined`. */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const response = await send(path, options, 'application/json')
  if (!response.ok) throw await toApiError(response)
  const data = response.status === 204 ? undefined : await response.json()
  return { data: data as T, etag: response.headers.get('ETag'), status: response.status, headers: response.headers }
}

/** A binary download (PDFs), fetched as a blob so errors stay inside the app (docs/08 §17). */
export async function apiBlob(path: string, options: RequestOptions = {}): Promise<{ blob: Blob; headers: Headers }> {
  const response = await send(path, options, 'application/pdf, application/problem+json')
  if (!response.ok) throw await toApiError(response)
  return { blob: await response.blob(), headers: response.headers }
}

export function isApiError(error: unknown, code?: string): error is ApiError {
  return error instanceof ApiError && (code === undefined || error.code === code)
}
