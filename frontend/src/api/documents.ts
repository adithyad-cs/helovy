/** Documents: E-13 to E-23 (docs/07 §3.3, §4). Money and quantities are strings throughout. */
import { keepPreviousData, useInfiniteQuery, useQuery } from '@tanstack/react-query'

import type { Versioned } from './businesses'
import { apiBlob, apiRequest } from './http'
import { queryKeys } from './queryKeys'

export type DiscountType = 'none' | 'percent' | 'amount'

export interface LineInput {
  description: string
  quantity: string
  unit: string | null
  unit_price: string
  discount_type: DiscountType
  discount_value: string | null
}

export interface DocumentLine extends LineInput {
  position: number
  gross: string
  discount: string
  line_total: string
}

export interface Totals {
  gross_total: string
  discount_total: string
  grand_total: string
}

export type PdfStatus = 'pending' | 'ready' | 'failed'

export interface PdfInfo {
  status: PdfStatus
  sha256: string | null
  size_bytes: number | null
  rendered_at: string | null
  attempts: number
  last_error_code: string | null
  retry_available: boolean
}

export interface InvoiceDocument {
  id: string
  business_id: string
  doc_type: 'invoice'
  status: 'draft' | 'finalized'
  tax_mode: 'no_tax'
  template_id: string
  currency: 'INR'
  customer: { id: string; display_name: string }
  number: string | null
  issue_date: string | null
  due_date: string | null
  reference: string | null
  notes: string | null
  terms: string | null
  lines: DocumentLine[]
  totals: Totals
  calc_version: string
  finalized_at: string | null
  snapshot_sha256: string | null
  pdf: PdfInfo | null
  version: number
  created_at: string
  updated_at: string
  seller?: SellerSnapshot | null
  buyer?: BuyerSnapshot | null
}

export interface AddressSnapshot {
  line1: string | null
  line2: string | null
  city: string | null
  state_code: string | null
  state_name: string | null
  postal_code: string | null
  country_code: string
}

export interface SellerSnapshot {
  legal_name: string
  trade_name: string | null
  address: AddressSnapshot
  phone: string | null
  email: string | null
  gstin: string | null
}

export interface BuyerSnapshot {
  display_name: string
  contact_name: string | null
  email: string | null
  phone: string | null
  address: AddressSnapshot
  gstin: string | null
}

export interface DraftFields {
  customer_id: string
  template_id: string
  reference: string | null
  due_date: string | null
  notes: string | null
  terms: string | null
  lines: LineInput[]
}

export interface Calculation {
  calc_version: string
  lines: Array<{ position: number; gross: string; discount: string; line_total: string }>
  totals: Totals
}

export interface Template {
  id: string
  code: string
  version: number
  name: string
  description: string
  tier: 'free'
  doc_type: 'invoice'
}

function versioned<T extends { version: number }>(data: T, etag: string | null): Versioned<T> {
  return { data, etag: etag ?? `"${data.version}"` }
}

export async function getDocument(id: string): Promise<Versioned<InvoiceDocument>> {
  const { data, etag } = await apiRequest<InvoiceDocument>(`/api/v1/documents/${id}`)
  return versioned(data, etag)
}

export function useDocument(
  id: string,
  options: { refetchInterval?: (data: Versioned<InvoiceDocument> | undefined) => number | false } = {},
) {
  const interval = options.refetchInterval
  return useQuery({
    queryKey: queryKeys.document(id),
    queryFn: () => getDocument(id),
    refetchInterval: interval ? (query) => interval(query.state.data) : undefined,
  })
}

export async function createDraft(businessId: string, customerId: string): Promise<Versioned<InvoiceDocument>> {
  const { data, etag } = await apiRequest<InvoiceDocument>(`/api/v1/businesses/${businessId}/documents`, {
    method: 'POST',
    body: { customer_id: customerId },
  })
  return versioned(data, etag)
}

export async function saveDraft(id: string, fields: Partial<DraftFields>, ifMatch: string): Promise<Versioned<InvoiceDocument>> {
  const { data, etag } = await apiRequest<InvoiceDocument>(`/api/v1/documents/${id}`, {
    method: 'PATCH',
    body: fields,
    ifMatch,
  })
  return versioned(data, etag)
}

export async function deleteDraft(id: string, ifMatch: string): Promise<void> {
  await apiRequest<void>(`/api/v1/documents/${id}`, { method: 'DELETE', ifMatch })
}

export async function calculate(
  businessId: string,
  lines: Array<Pick<LineInput, 'quantity' | 'unit_price' | 'discount_type' | 'discount_value'>>,
  signal?: AbortSignal,
): Promise<Calculation> {
  const { data } = await apiRequest<Calculation>(`/api/v1/businesses/${businessId}/calculate`, {
    method: 'POST',
    body: { lines },
    signal,
  })
  return data
}

export async function listTemplates(): Promise<Template[]> {
  const { data } = await apiRequest<{ items: Template[] }>('/api/v1/templates?doc_type=invoice')
  return data.items
}

export function useTemplates() {
  return useQuery({ queryKey: queryKeys.templates, queryFn: listTemplates, staleTime: 5 * 60_000 })
}

export async function previewPdf(id: string): Promise<Blob> {
  const { blob } = await apiBlob(`/api/v1/documents/${id}/preview.pdf`)
  return blob
}

export async function finalizeDocument(id: string, ifMatch: string, idempotencyKey: string): Promise<Versioned<InvoiceDocument>> {
  const { data, etag } = await apiRequest<InvoiceDocument>(`/api/v1/documents/${id}/finalize`, {
    method: 'POST',
    ifMatch,
    idempotencyKey,
  })
  return versioned(data, etag)
}

export async function retryPdf(id: string): Promise<{ pdf: PdfInfo }> {
  const { data } = await apiRequest<{ pdf: PdfInfo }>(`/api/v1/documents/${id}/pdf/render`, { method: 'POST' })
  return data
}

export async function downloadPdf(id: string): Promise<Blob> {
  const { blob } = await apiBlob(`/api/v1/documents/${id}/pdf`)
  return blob
}

export interface DocumentListItem {
  id: string
  status: 'draft' | 'finalized'
  number: string | null
  customer_name: string
  issue_date: string | null
  grand_total: string | null
  pdf_status: PdfStatus | null
  created_at: string
  updated_at: string
}

export interface DocumentPage {
  items: DocumentListItem[]
  next_cursor: string | null
}

export async function listDocuments(
  businessId: string,
  params: { status?: 'draft' | 'finalized'; q?: string; cursor?: string | null; limit?: number },
): Promise<DocumentPage> {
  const search = new URLSearchParams()
  if (params.status) search.set('status', params.status)
  if (params.q) search.set('q', params.q)
  if (params.cursor) search.set('cursor', params.cursor)
  search.set('limit', String(params.limit ?? 20))
  const { data } = await apiRequest<DocumentPage>(`/api/v1/businesses/${businessId}/documents?${search.toString()}`)
  return data
}

export function useDocumentList(businessId: string, params: { status?: 'draft' | 'finalized'; q?: string; limit?: number }) {
  return useInfiniteQuery({
    queryKey: queryKeys.documents(businessId, params),
    queryFn: ({ pageParam }) => listDocuments(businessId, { ...params, cursor: pageParam }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    placeholderData: keepPreviousData,
  })
}
