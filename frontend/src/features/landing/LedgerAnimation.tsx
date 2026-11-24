import { useEffect, useRef, useState } from 'react'

import { LockIcon } from '../../components/ui/icons'

/**
 * "The Ledger Assembles" (docs/08 §10.2): three beats in under 5 s, played once when the panel
 * enters the viewport. CSS keyframes only (no animation library). Under
 * `prefers-reduced-motion: reduce` the final frame is shown at once. The figures are the
 * fixture values F-01 and F-02 (illustrative, docs/15 rule 11); nothing here is live data.
 */
export function LedgerAnimation() {
  const ref = useRef<HTMLDivElement>(null)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (typeof IntersectionObserver !== 'function') {
      const timer = setTimeout(() => setPlaying(true), 0)
      return () => clearTimeout(timer)
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setPlaying(true)
          observer.disconnect()
        }
      },
      { threshold: 0.35 },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  return (
    <figure className="m-0" aria-labelledby="ledger-caption">
      <div ref={ref} data-playing={playing ? 'true' : 'false'} className="ledger relative mx-auto w-full max-w-[440px]" aria-hidden="true">
        <div className="ledger-sheet relative rounded-[6px] border border-line bg-surface px-6 pt-6 pb-7 shadow-[0_18px_40px_-18px_rgba(27,42,65,0.35)] md:px-8">
          <span className="absolute top-3 right-3 rounded-[3px] border border-ink-muted/40 px-1.5 py-0.5 text-[9px] font-semibold tracking-[0.18em] text-ink-muted">
            SPECIMEN
          </span>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[13px] font-semibold text-ink">Lotus Lane Design Studio (Demo)</p>
              <p className="text-[11px] text-ink-muted">Bengaluru · Karnataka</p>
            </div>
            <p className="font-serif text-xl font-semibold text-ink">Invoice</p>
          </div>
          <div className="mt-3 h-[1.5px] bg-accent" />
          <p className="mt-3 text-[10px] font-semibold tracking-[0.14em] text-ink-muted">BILL TO</p>
          <p className="text-[12px] font-medium text-ink">Riverstone Consulting (Demo)</p>

          <div className="mt-4 border-t border-line text-[11.5px] md:text-[12px]">
            <div className="ledger-line ledger-line-1 grid grid-cols-[1fr_auto] gap-x-3 border-b border-line py-2">
              <span className="text-ink">Brand identity consultation</span>
              <span className="text-right font-semibold text-ink tabular-nums">₹1,800.00</span>
              <span className="text-[10.5px] text-ink-muted tabular-nums">2.5 × ₹800.00 · −10%</span>
            </div>
            <div className="ledger-line ledger-line-2 grid grid-cols-[1fr_auto] gap-x-3 border-b border-line py-2">
              <span className="text-ink">Website support hours</span>
              <span className="text-right font-semibold text-ink tabular-nums">₹900.00</span>
              <span className="text-[10.5px] text-ink-muted tabular-nums">3 × ₹333.33 · −₹99.99</span>
            </div>
            {/* Ruled lines that the sheet starts with. */}
            <div className="border-b border-line/60 py-3" />
          </div>

          <div className="mt-4 flex flex-col-reverse items-start gap-4 md:flex-row md:items-end md:justify-between">
            <div className="ledger-stamp flex -rotate-[6deg] items-center gap-2 rounded-[4px] border-2 border-accent bg-surface px-3 py-1.5 text-accent">
              <LockIcon width={16} height={16} />
              <span className="text-[10.5px] font-bold tracking-[0.1em] whitespace-nowrap tabular-nums md:text-[11px]">FINALISED · INV/26-27/00001</span>
            </div>
            <dl className="ledger-totals w-full max-w-[12.5rem] self-end text-[12px] tabular-nums">
              <div className="flex justify-between py-0.5">
                <dt className="text-ink-muted">Subtotal</dt>
                <dd className="text-ink">₹2,999.99</dd>
              </div>
              <div className="flex justify-between py-0.5">
                <dt className="text-ink-muted">Discount</dt>
                <dd className="text-ink">−₹299.99</dd>
              </div>
              <div className="relative mt-1 flex justify-between border-t border-ink pt-1.5 text-[14px] font-semibold">
                <dt className="text-ink">Total</dt>
                <dd className="text-ink">₹2,700.00</dd>
                <span className="ledger-sweep absolute right-0 -bottom-1.5 left-0 h-[3px] origin-left rounded-full bg-accent/70" />
              </div>
            </dl>
          </div>
        </div>
        <p className="ledger-caption mt-4 text-center text-sm font-medium text-ink">Numbered once. Locked.</p>
      </div>
      <figcaption id="ledger-caption" className="sr-only">
        An invoice is filled with two lines, the server calculates a total of ₹2,700.00, and it is finalised as INV/26-27/00001.
      </figcaption>
    </figure>
  )
}
