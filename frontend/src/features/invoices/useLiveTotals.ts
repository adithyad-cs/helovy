import { useEffect, useMemo, useRef, useState } from 'react'

import { calculate, type Calculation, type InvoiceDocument } from '../../api/documents'
import { ApiError } from '../../api/http'
import { isBlankLine, numericLine, type LineForm } from './editorModel'

export interface LineAmounts {
  gross: string
  discount: string
  line_total: string
}

export interface LiveTotals {
  calculating: boolean
  /** Amounts per form line index; null when the line is blank or invalid. */
  lines: Array<LineAmounts | null>
  totals: Calculation['totals'] | null
  /** Server field messages per form line: { index: { field: message } }. */
  lineErrors: Record<number, Record<string, string>>
  error: unknown
  updatedAt: number
}

interface Settled {
  key: string
  map: number[]
  result: Calculation | null
  error: unknown
  updatedAt: number
}

/**
 * Live server totals (docs/04 §4; docs/08 §15.3): the current lines go to E-14, debounced by
 * 400 ms; responses older than the latest request are ignored. The browser never calculates.
 */
export function useLiveTotals(businessId: string, lines: LineForm[], initial: InvoiceDocument): LiveTotals {
  const included = lines.flatMap((line, index) => (isBlankLine(line) ? [] : [index]))
  const key = JSON.stringify(included.map((index) => numericLine(lines[index] as LineForm)))
  const mapKey = included.join(',')
  const sequence = useRef(0)
  const [settled, setSettled] = useState<Settled>(() => ({
    key,
    map: included,
    result: { calc_version: initial.calc_version, lines: initial.lines.map((l) => ({ position: l.position, gross: l.gross, discount: l.discount, line_total: l.line_total })), totals: initial.totals },
    error: null,
    updatedAt: 0,
  }))
  const payload = useMemo(() => JSON.parse(key) as ReturnType<typeof numericLine>[], [key])
  const map = useMemo(() => (mapKey === '' ? [] : mapKey.split(',').map(Number)), [mapKey])

  useEffect(() => {
    if (key === settled.key) return
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      const mine = ++sequence.current
      calculate(businessId, payload, controller.signal)
        .then((result) => {
          if (mine === sequence.current) setSettled({ key, map, result, error: null, updatedAt: Date.now() })
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === 'AbortError') return
          if (mine === sequence.current) setSettled({ key, map, result: null, error, updatedAt: Date.now() })
        })
    }, 400)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [businessId, key, map, payload, settled.key])

  const lineErrors: Record<number, Record<string, string>> = {}
  if (settled.error instanceof ApiError && settled.error.code === 'validation_failed') {
    for (const item of settled.error.fieldErrors) {
      const match = /^\/lines\/(\d+)\/(\w+)$/.exec(item.pointer)
      if (!match) continue
      const formIndex = settled.map[Number(match[1])]
      if (formIndex === undefined) continue
      lineErrors[formIndex] = { ...(lineErrors[formIndex] ?? {}), [match[2] as string]: item.message }
    }
  }

  const amounts: Array<LineAmounts | null> = lines.map(() => null)
  if (settled.result) {
    settled.result.lines.forEach((line, position) => {
      const formIndex = settled.map[position]
      if (formIndex !== undefined && formIndex < amounts.length) amounts[formIndex] = line
    })
  }

  return {
    calculating: key !== settled.key,
    lines: amounts,
    totals: settled.result?.totals ?? null,
    lineErrors,
    error: settled.error,
    updatedAt: settled.updatedAt,
  }
}
