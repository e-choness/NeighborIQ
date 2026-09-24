/** Hex-map metrics (kept separate from lib/hex.ts so pages don't bundle h3-js). */
export type HexMetric = 'gross_yield_pct' | 'price_per_sqft' | 'price_cut_pct' | 'days_on_market'

export const HEX_METRICS: Record<HexMetric, { label: string; short: string; format: (v: number) => string; higherIs: string }> = {
  gross_yield_pct: { label: 'Gross rental yield', short: 'Yield', format: (v) => `${v.toFixed(1)}%`, higherIs: 'more rent per dollar' },
  price_per_sqft: { label: 'Asking price per sq ft', short: '$/sq ft', format: (v) => `$${Math.round(v).toLocaleString('en-CA')}`, higherIs: 'more expensive' },
  price_cut_pct: { label: 'Average price cut', short: 'Price cuts', format: (v) => `${v.toFixed(1)}%`, higherIs: 'bigger reductions' },
  days_on_market: { label: 'Days on market', short: 'Days listed', format: (v) => `${Math.round(v)} d`, higherIs: 'slower to sell' },
}
