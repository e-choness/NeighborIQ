/**
 * Client-side H3 aggregation of listing points into hexagons for the map.
 * Resolution 8 cells are ~0.74 km² — about a few city blocks.
 */
import { cellToBoundary, latLngToCell } from 'h3-js'
import { HEX_METRICS, type HexMetric } from './metrics'
import type { MarketPoints } from './types'

export { HEX_METRICS, type HexMetric }

export interface HexFeatureProps {
  cell: string
  count: number
  value: number
  gross_yield_pct: number | null
  price_per_sqft: number | null
  price_cut_pct: number | null
  days_on_market: number | null
}

function median(values: number[]): number | null {
  if (!values.length) return null
  const s = [...values].sort((a, b) => a - b)
  const mid = s.length >> 1
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2
}

function mean(values: number[]): number | null {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : null
}

export function aggregateHexes(points: MarketPoints, metric: HexMetric, resolution = 8) {
  const col = Object.fromEntries(points.columns.map((c, i) => [c, i]))
  const metrics = Object.keys(HEX_METRICS) as HexMetric[]
  const cells = new Map<string, { count: number; values: Record<HexMetric, number[]> }>()
  for (const row of points.rows) {
    const cell = latLngToCell(row[col.lat] as number, row[col.lon] as number, resolution)
    let bucket = cells.get(cell)
    if (!bucket) {
      bucket = { count: 0, values: { gross_yield_pct: [], price_per_sqft: [], price_cut_pct: [], days_on_market: [] } }
      cells.set(cell, bucket)
    }
    bucket.count += 1
    for (const key of metrics) {
      const value = row[col[key]]
      if (value !== null && value !== undefined) bucket.values[key].push(value as number)
    }
  }

  const features = []
  for (const [cell, { count, values }] of cells) {
    const props: HexFeatureProps = {
      cell,
      count,
      gross_yield_pct: median(values.gross_yield_pct),
      price_per_sqft: median(values.price_per_sqft),
      // Price cuts: the average across all listings (a zero means no cut)
      price_cut_pct: mean(values.price_cut_pct),
      days_on_market: median(values.days_on_market),
      value: 0,
    }
    const value = props[metric]
    if (value === null) continue
    props.value = value
    features.push({
      type: 'Feature' as const,
      properties: props,
      geometry: { type: 'Polygon' as const, coordinates: [cellToBoundary(cell, true)] },
    })
  }
  return { type: 'FeatureCollection' as const, features }
}

/** Robust colour/height domain: 5th–95th percentile of hex values. */
export function domain(values: number[]): [number, number] {
  if (!values.length) return [0, 1]
  const s = [...values].sort((a, b) => a - b)
  const at = (q: number) => s[Math.min(s.length - 1, Math.max(0, Math.round(q * (s.length - 1))))]
  const lo = at(0.05)
  const hi = at(0.95)
  return lo === hi ? [lo, lo + 1] : [lo, hi]
}
