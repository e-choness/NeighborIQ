const cad0 = new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 })

export function money(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : cad0.format(value).replace('CA', '')
}

/** $1.30M · $849K · $950 */
export function moneyShort(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const abs = Math.abs(value)
  const sign = value < 0 ? '−' : ''
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(abs >= 10_000_000 ? 1 : 2)}M`
  if (abs >= 10_000) return `${sign}$${Math.round(abs / 1000)}K`
  return `${sign}$${Math.round(abs).toLocaleString('en-CA')}`
}

/** Signed monthly amount with a true minus sign: +$120 / −$4,492 */
export function signedMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const rounded = Math.round(value)
  return `${rounded < 0 ? '−' : '+'}$${Math.abs(rounded).toLocaleString('en-CA')}`
}

export function pct(value: number | null | undefined, digits = 1): string {
  return value === null || value === undefined ? '—' : `${value.toFixed(digits)}%`
}

export function signedPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—'
  return `${value < 0 ? '−' : value > 0 ? '+' : ''}${Math.abs(value).toFixed(digits)}%`
}

export function num(value: number | null | undefined, digits = 0): string {
  return value === null || value === undefined ? '—' : value.toLocaleString('en-CA', { maximumFractionDigits: digits })
}

export function distance(metres: number): string {
  return metres < 1000 ? `${Math.round(metres / 10) * 10} m` : `${(metres / 1000).toFixed(1)} km`
}

export function date(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
}

export const PROPERTY_TYPE_LABEL: Record<string, string> = {
  condo: 'Condo',
  townhouse: 'Townhouse',
  semi: 'Semi-detached',
  detached: 'Detached',
}

export function beds(rooms: number | null | undefined): string {
  if (rooms === null || rooms === undefined) return '—'
  return rooms === 0 ? 'Studio' : `${rooms} bd`
}
