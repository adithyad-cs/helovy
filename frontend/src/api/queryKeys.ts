/** TanStack Query keys (docs/04 §4). */
export const queryKeys = {
  me: ['me'] as const,
  business: (id: string) => ['business', id] as const,
  customers: (businessId: string, params: object) => ['customers', businessId, params] as const,
  customersAll: (businessId: string) => ['customers', businessId] as const,
  customer: (id: string) => ['customer', id] as const,
  documents: (businessId: string, params: object) => ['documents', businessId, params] as const,
  documentsAll: (businessId: string) => ['documents', businessId] as const,
  document: (id: string) => ['document', id] as const,
  templates: ['templates'] as const,
}
