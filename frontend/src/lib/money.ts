/**
 * Display formatting for server strings (docs/09 §6). Strings in, strings out: money is never
 * converted to a binary floating-point Number (docs/15 §8). The server stays authoritative.
 */

const MONEY = /^(-?)(\d+)\.(\d{2})$/

/** Indian digit grouping: the last 3 digits, then groups of 2. `1234567` → `12,34,567`. */
function groupIndian(digits: string): string {
  if (digits.length <= 3) return digits
  const last3 = digits.slice(-3)
  let rest = digits.slice(0, -3)
  const groups: string[] = []
  while (rest.length > 2) {
    groups.unshift(rest.slice(-2))
    rest = rest.slice(0, -2)
  }
  if (rest) groups.unshift(rest)
  return `${groups.join(',')},${last3}`
}

/** `"123456.78"` → `₹1,23,456.78`; `"2700.00"` → `₹2,700.00`. Unknown shapes are shown as is. */
export function formatMoney(value: string | null | undefined): string {
  if (value == null) return '—'
  const match = MONEY.exec(value)
  if (!match) return value
  const [, sign, whole = '0', paise] = match
  return `${sign ? '−' : ''}₹${groupIndian(whole.replace(/^0+(?=\d)/, ''))}.${paise}`
}

/** A discount shown as a deduction: `"299.99"` → `−₹299.99`; zero stays `₹0.00`. */
export function formatDeduction(value: string | null | undefined): string {
  if (value == null) return '—'
  return /^0+\.00$/.test(value) ? formatMoney(value) : `−${formatMoney(value)}`
}

/** Trailing zeros after the point removed: `"2.500"` → `2.5`; `"3.000"` → `3`. */
export function formatQuantity(value: string): string {
  if (!value.includes('.')) return value
  return value.replace(/0+$/, '').replace(/\.$/, '')
}

/** `"10.00"` → `10%`; `"12.50"` → `12.5%`. */
export function formatPercent(value: string): string {
  return `${formatQuantity(value)}%`
}
