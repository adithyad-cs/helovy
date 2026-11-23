/** E-06, E-07, E-08 (docs/07 §4). The ETag travels with the data for If-Match. */
import { useQuery } from '@tanstack/react-query'

import { apiRequest } from './http'
import { queryKeys } from './queryKeys'

export interface Business {
  id: string
  legal_name: string
  trade_name: string | null
  address_line1: string
  address_line2: string | null
  city: string
  state_code: string
  state_name: string | null
  postal_code: string
  country_code: 'IN'
  phone: string | null
  email: string | null
  gstin: string | null
  version: number
  created_at: string
  updated_at: string
}

export type BusinessInput = Omit<Business, 'id' | 'state_name' | 'version' | 'created_at' | 'updated_at' | 'country_code'>

export interface Versioned<T> {
  data: T
  etag: string
}

export async function getBusiness(id: string): Promise<Versioned<Business>> {
  const { data, etag } = await apiRequest<Business>(`/api/v1/businesses/${id}`)
  return { data, etag: etag ?? `"${data.version}"` }
}

export function useBusiness(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.business(id ?? 'none'),
    queryFn: () => getBusiness(id as string),
    enabled: Boolean(id),
  })
}

export async function createBusiness(input: Partial<BusinessInput>): Promise<Versioned<Business>> {
  const { data, etag } = await apiRequest<Business>('/api/v1/businesses', { method: 'POST', body: input })
  return { data, etag: etag ?? `"${data.version}"` }
}

export async function updateBusiness(id: string, changes: Partial<BusinessInput>, ifMatch: string): Promise<Versioned<Business>> {
  const { data, etag } = await apiRequest<Business>(`/api/v1/businesses/${id}`, {
    method: 'PATCH',
    body: changes,
    ifMatch,
  })
  return { data, etag: etag ?? `"${data.version}"` }
}
