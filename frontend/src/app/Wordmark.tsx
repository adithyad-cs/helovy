/** The HIVE DOCS wordmark: a hexagonal ledger mark and the name, in ink. */
export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 text-ink">
      <svg aria-hidden="true" viewBox="0 0 32 32" width={compact ? 26 : 30} height={compact ? 26 : 30}>
        <path d="M16 2.5 28 9.25v13.5L16 29.5 4 22.75V9.25z" fill="var(--ink)" />
        <path d="M11 11.5h10M11 15.5h10M11 19.5h6" stroke="var(--paper)" strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="21.5" cy="20.5" r="2.25" fill="var(--accent)" />
      </svg>
      <span className={compact ? 'text-[15px] font-semibold tracking-[0.14em]' : 'text-lg font-semibold tracking-[0.16em]'}>
        HIVE DOCS
      </span>
    </span>
  )
}
