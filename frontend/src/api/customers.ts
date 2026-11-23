/** E-09 to E-12 (docs/07 §4). */
import { keepPreviousData, useInfiniteQuery, useQuery } from '@tanstack/react-query'

import type { Versioned } from './businesses'
import { apiRequest } from './http'
import { queryKeys } from './queryKeys'

export interface Customer {
  id: string
  display_name: string
  contact_name: string | null
  email: string | null
  phone: string | null
  address_line1: string | null
  address_line2: string | null
  city: string | null
  state_code: string | null
  state_name: string | null
  postal_code: string | null
  country_code: 'IN'
  gstin: string | null
  version: number
  created_at: string
  updated_at: string
}

export type CustomerSummary = Pick<Customer, 'id' | 'display_name' | 'contact_name' | 'email' | 'city' | 'created_at'>
export type CustomerInput = Omit<Customer, 'id' | 'state_name' | 'version' | 'created_at' | 'updated_at' | 'country_code'>

export interface Page<T> {
  items: T[]
  next_cursor: string | null
}

function base(businessId: string) {
  return `/api/v1/businesses/${businessId}/customers`
}

export async function listCustomers(businessId: string, params: { q?: string; cursor?: string | null; limit?: number }) {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.cursor) search.set('cursor', params.cursor)
  search.set('limit', String(params.limit ?? 20))
  const { data } = await apiRequest<Page<CustomerSummary>>(`${base(businessId)}?${search.toString()}`)
  return data
}

export function useCustomerList(businessId: string, q: string, limit = 20) {
  return useInfiniteQuery({
    queryKey: queryKeys.customers(businessId, { q, limit }),
    queryFn: ({ pageParam }) => listCustomers(businessId, { q, cursor: pageParam, limit }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    placeholderData: keepPreviousData,
  })
}

export async function getCustomer(businessId: string, id: string): Promise<Versioned<Customer>> {
  const { data, etag } = await apiRequest<Customer>(`${base(businessId)}/${id}`)
  return { data, etag: etag ?? `"${data.version}"` }
}

export function useCustomer(businessId: string, id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.customer(id ?? 'new'),
    queryFn: () => getCustomer(businessId, id as string),
    enabled: Boolean(id),
  })
}

export async function createCustomer(businessId: string, input: Partial<CustomerInput>): Promise<Versioned<Customer>> {
  const { data, etag } = await apiRequest<Customer>(base(businessId), { method: 'POST', body: input })
  return { data, etag: etag ?? `"${data.version}"` }
}

export async function updateCustomer(
  businessId: string,
  id: string,
  changes: Partial<CustomerInput>,
  ifMatch: string,
): Promise<Versioned<Customer>> {
  const { data, etag } = await apiRequest<Customer>(`${base(businessId)}/${id}`, {
    method: 'PATCH',
    body: changes,
    ifMatch,
  })
  return { data, etag: etag ?? `"${data.version}"` }
}
