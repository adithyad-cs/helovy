/** One key per Finalise confirmation, reused for automatic retries of that attempt (docs/04 §4). */
export function newIdempotencyKey(): string {
  return crypto.randomUUID()
}

export function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}
