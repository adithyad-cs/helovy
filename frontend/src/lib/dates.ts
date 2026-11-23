/** Dates as `DD Mon YYYY` (docs/09 §6), in the Asia/Kolkata calendar for timestamps. */
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** `2026-11-25` → `25 Nov 2026` (a calendar date; no time-zone conversion). */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) return value
  const [, year, month, day] = match
  return `${day} ${MONTHS[Number(month) - 1] ?? month} ${year}`
}

const IST = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' })
const IST_TIME = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false })

/** An RFC 3339 timestamp → its India calendar date, `DD Mon YYYY`. */
export function formatTimestampDate(value: string | null | undefined): string {
  if (!value) return '—'
  return formatDate(IST.format(new Date(value)))
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) return '—'
  return `${formatTimestampDate(value)}, ${IST_TIME.format(new Date(value))} IST`
}
