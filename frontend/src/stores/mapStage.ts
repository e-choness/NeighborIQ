/**
 * What the one persistent map shows. Pages set it in onMounted/watch; MapStage reacts.
 *
 * - home:     3D hex columns of the city (metric), slow orbit
 * - explore:  flat, listing dots (`listings`), fitted to them or to `bbox`
 * - listing:  the subject and its comparables, flown to at street level
 * - overview: dimmed hex columns behind a centre sheet (Portfolio, Data), plus `listings` dots if any
 */
import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import type { HexMetric } from '@/lib/metrics'

export type StageMode = 'home' | 'explore' | 'listing' | 'overview'
export type BBox = [number, number, number, number]

export interface StagePoint {
  id: number
  latitude: number | null
  longitude: number | null
  gross_yield_pct: number | null
}
export interface StageComp {
  id: number
  latitude: number
  longitude: number
}

export const useMapStage = defineStore('mapStage', () => {
  const mode = ref<StageMode>('home')
  const metric = ref<HexMetric>('gross_yield_pct')
  /** Hex colour/height domain, reported back by the map for the Home legend. */
  const range = ref<[number, number]>([0, 1])
  const listings = shallowRef<StagePoint[]>([])
  const bbox = ref<BBox | null>(null)
  const subject = ref<{ latitude: number; longitude: number } | null>(null)
  const comps = shallowRef<StageComp[]>([])
  const zoom = ref(14.2)
  const highlightId = ref<number | null>(null)
  const highlightComp = ref<number | null>(null)
  /** Set by the map's "Search this area" button; Explore consumes it. */
  const areaRequest = ref<BBox | null>(null)

  /** Switch mode and replace the per-screen data in one go (pages then update fields as queries load). */
  function show(
    next: StageMode,
    opts: {
      listings?: StagePoint[]
      subject?: { latitude: number; longitude: number } | null
      comps?: StageComp[]
      bbox?: BBox | null
      zoom?: number
    } = {},
  ) {
    mode.value = next
    listings.value = opts.listings ?? []
    subject.value = opts.subject ?? null
    comps.value = opts.comps ?? []
    bbox.value = opts.bbox ?? null
    zoom.value = opts.zoom ?? 14.2
    highlightId.value = null
    highlightComp.value = null
  }

  return { mode, metric, range, listings, bbox, subject, comps, zoom, highlightId, highlightComp, areaRequest, show }
})
