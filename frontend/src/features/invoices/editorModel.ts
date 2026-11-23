/** Editor form model and client-side checks mirroring docs/09 §4 (instant feedback only). */
import { z } from 'zod'

import type { DiscountType, DraftFields, InvoiceDocument } from '../../api/documents'

export interface LineForm {
  description: string
  quantity: string
  unit: string
  unit_price: string
  discount_type: DiscountType
  discount_value: string
}

export interface EditorValues {
  customer: { id: string; display_name: string }
  template_id: string
  reference: string
  due_date: string
  notes: string
  terms: string
  lines: LineForm[]
}

export const MAX_LINES = 200
export const EMPTY_LINE: LineForm = { description: '', quantity: '1', unit: '', unit_price: '', discount_type: 'none', discount_value: '' }

const PLAIN = /^(0|[1-9]\d*)(\.(\d+))?$/

/** Compares two plain decimal strings without converting them to binary numbers. */
export function compareDecimal(a: string, b: string): number {
  const [ai = '0', af = ''] = a.split('.')
  const [bi = '0', bf = ''] = b.split('.')
  const aInt = ai.replace(/^0+(?=\d)/, '')
  const bInt = bi.replace(/^0+(?=\d)/, '')
  if (aInt.length !== bInt.length) return aInt.length < bInt.length ? -1 : 1
  if (aInt !== bInt) return aInt < bInt ? -1 : 1
  const width = Math.max(af.length, bf.length)
  const aFrac = af.padEnd(width, '0')
  const bFrac = bf.padEnd(width, '0')
  if (aFrac === bFrac) return 0
  return aFrac < bFrac ? -1 : 1
}

interface DecimalRule {
  decimals: number
  max: string
  allowZero: boolean
  empty: string
  range: string
}

const RULES = {
  quantity: { decimals: 3, max: '1000000', allowZero: false, empty: 'Enter a quantity.', range: 'Enter a quantity above 0 and up to 10,00,000.' },
  unit_price: { decimals: 2, max: '10000000', allowZero: true, empty: 'Enter a unit price.', range: 'Enter a price from ₹0.00 to ₹1,00,00,000.00.' },
  percent: { decimals: 2, max: '100', allowZero: false, empty: 'Enter the discount percentage.', range: 'Enter a percentage above 0 and up to 100.' },
  amount: { decimals: 2, max: '99999999.99', allowZero: false, empty: 'Enter the discount amount.', range: 'Enter a discount above ₹0.00.' },
} satisfies Record<string, DecimalRule>

export function decimalIssue(raw: string, rule: DecimalRule): string | null {
  const value = raw.trim()
  if (value === '') return rule.empty
  const match = PLAIN.exec(value)
  if (!match) return 'Enter a number such as 2.5, without signs or spaces.'
  if ((match[3] ?? '').length > rule.decimals) return `Use at most ${rule.decimals} decimal places.`
  const zero = !/[1-9]/.test(value)
  if ((zero && !rule.allowZero) || compareDecimal(value, rule.max) > 0) return rule.range
  return null
}

const lineSchema = z
  .object({
    description: z.string().trim().min(1, 'Enter a description.').max(500, 'Use at most 500 characters.'),
    quantity: z.string(),
    unit: z.string().trim().max(20, 'Use at most 20 characters.'),
    unit_price: z.string(),
    discount_type: z.enum(['none', 'percent', 'amount']),
    discount_value: z.string(),
  })
  .superRefine((line, ctx) => {
    const add = (path: keyof LineForm, message: string | null) => {
      if (message) ctx.addIssue({ code: 'custom', path: [path], message })
    }
    add('quantity', decimalIssue(line.quantity, RULES.quantity))
    add('unit_price', decimalIssue(line.unit_price, RULES.unit_price))
    if (line.discount_type === 'percent') add('discount_value', decimalIssue(line.discount_value, RULES.percent))
    if (line.discount_type === 'amount') add('discount_value', decimalIssue(line.discount_value, RULES.amount))
  })

export const editorSchema = z.object({
  customer: z.object({ id: z.string().min(1, 'Choose a customer.'), display_name: z.string() }),
  template_id: z.string().min(1, 'Choose a template.'),
  reference: z.string().trim().max(100, 'Use at most 100 characters.'),
  due_date: z
    .string()
    .refine((v) => v === '' || (/^\d{4}-\d{2}-\d{2}$/.test(v) && v >= '2020-01-01' && v <= '2099-12-31'), 'Choose a date between 2020 and 2099.'),
  notes: z.string().max(2000, 'Use at most 2,000 characters.'),
  terms: z.string().max(2000, 'Use at most 2,000 characters.'),
  lines: z.array(lineSchema).max(MAX_LINES, `Use at most ${MAX_LINES} lines.`),
})

export function toEditorValues(document: InvoiceDocument): EditorValues {
  return {
    customer: { id: document.customer.id, display_name: document.customer.display_name },
    template_id: document.template_id,
    reference: document.reference ?? '',
    due_date: document.due_date ?? '',
    notes: document.notes ?? '',
    terms: document.terms ?? '',
    lines: document.lines.map((line) => ({
      description: line.description,
      quantity: trimDecimal(line.quantity),
      unit: line.unit ?? '',
      unit_price: line.unit_price,
      discount_type: line.discount_type,
      discount_value: line.discount_value ? trimDecimal(line.discount_value) : '',
    })),
  }
}

/** "2.500" → "2.5" for editing (strings only). */
function trimDecimal(value: string): string {
  return value.includes('.') ? value.replace(/0+$/, '').replace(/\.$/, '') : value
}

function optionalText(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

export function numericLine(line: LineForm) {
  return {
    quantity: line.quantity.trim(),
    unit_price: line.unit_price.trim(),
    discount_type: line.discount_type,
    discount_value: line.discount_type === 'none' ? null : line.discount_value.trim(),
  }
}

export function toDraftFields(values: EditorValues): DraftFields {
  return {
    customer_id: values.customer.id,
    template_id: values.template_id,
    reference: optionalText(values.reference),
    due_date: values.due_date || null,
    notes: optionalText(values.notes.replace(/\r\n/g, '\n')),
    terms: optionalText(values.terms.replace(/\r\n/g, '\n')),
    lines: values.lines.map((line) => ({
      description: line.description.trim(),
      unit: optionalText(line.unit),
      ...numericLine(line),
    })),
  }
}

/** A brand-new row with no quantity and no price is not sent for calculation yet. */
export function isBlankLine(line: LineForm): boolean {
  return line.unit_price.trim() === '' && line.description.trim() === ''
}
