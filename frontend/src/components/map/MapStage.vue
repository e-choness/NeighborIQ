<script setup lang="ts">
/**
 * The one MapLibre map behind every map screen (replaces HexMap3D, ListingsMap and CompsMap).
 * Driven by stores/mapStage.ts; see that file for what each mode shows.
 *
 * Hex columns encode the metric in height and colour (colour is never the only channel). The
 * camera orbits slowly on Home until the viewer interacts; reduced-motion users get a still map.
 */
import { useQuery } from '@pinia/colada'
import { Marker, type GeoJSONSource, type Map as MapLibreMap, type MapLayerMouseEvent } from 'maplibre-gl'
import type { Feature, FeatureCollection, Point } from 'geojson'
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/lib/api'
import { aggregateHexes, domain, HEX_METRICS, type HexFeatureProps, type HexMetric } from '@/lib/hex'
import { basemapFailed, createMap, fitPadding, onStyle, rampStops, styleFor, tintBasemap } from '@/lib/map'
import { prefersReducedMotion, theme } from '@/lib/theme'
import type { MarketPoints } from '@/lib/types'
import { isPhone, showBestRow, showStatTiles } from '@/lib/viewport'
import { useCity } from '@/stores/city'
import { useMapStage } from '@/stores/mapStage'
import { useShell } from '@/stores/shell'
import { DIVERGING, HOVER, MARKERS, SEQUENTIAL, STROKE } from '@/theme/palette'

const stage = useMapStage()
const cities = useCity()
const shell = useShell()
const route = useRoute()
const router = useRouter()

const container = useTemplateRef<HTMLDivElement>('container')
const map = shallowRef<MapLibreMap>()
const loaded = ref(false)
const hover = ref<{ x: number; y: number; props: HexFeatureProps } | null>(null)
/** Explore: the viewer panned or zoomed, so stop refitting and offer "Search this area". */
const moved = ref(false)

const { data: points } = useQuery({
  key: () => ['market-points', cities.city],
  query: () => api<MarketPoints>(`/markets/${encodeURIComponent(cities.city)}/points`),
  enabled: () => Boolean(cities.city),
})
const { data: communities } = useQuery({
  key: () => ['communities', cities.city],
  query: () =>
    api<{ items: { name: string; latitude: number | null; longitude: number | null }[] }>('/communities', {
      query: { city: cities.city },
    }),
  enabled: () => Boolean(cities.city),
})

type FC = { type: 'FeatureCollection'; features: Feature[] }
const EMPTY: FC = { type: 'FeatureCollection', features: [] }

const hexes = computed(() => (points.value ? aggregateHexes(points.value, stage.metric) : null))
const hexDomain = computed<[number, number]>(() => domain(hexes.value?.features.map((f) => f.properties.value) ?? []))
watch(hexDomain, (d) => (stage.range = d), { immediate: true })

const pts = computed<FC>(() => ({
  type: 'FeatureCollection',
  features: stage.listings
    .filter((l) => l.latitude !== null && l.longitude !== null)
    .map((l) => ({
      type: 'Feature',
      properties: { id: l.id, yield: l.gross_yield_pct ?? -1 },
      geometry: { type: 'Point', coordinates: [l.longitude!, l.latitude!] },
    })),
}))
const yieldDomain = computed(() =>
  domain(stage.listings.flatMap((l) => (l.gross_yield_pct === null ? [] : [l.gross_yield_pct]))),
)
const comps = computed<FC>(() => {
  const s = stage.subject
  if (!s) return EMPTY
  return {
    type: 'FeatureCollection',
    features: [
      ...stage.comps.map((c) => ({
        type: 'Feature' as const,
        properties: { kind: 'comp', id: c.id },
        geometry: { type: 'Point' as const, coordinates: [c.longitude, c.latitude] },
      })),
      {
        type: 'Feature',
        properties: { kind: 'subject', id: -1 },
        geometry: { type: 'Point', coordinates: [s.longitude, s.latitude] },
      },
    ],
  }
})

/** Where the map may frame data: the canvas minus the glass panels over it. */
const padding = computed(() => {
  if (isPhone.value) return { top: 120, left: 24, right: 24, bottom: shell.sheetHeight + 10 }
  if (route.name === 'home') {
    return { top: 100, left: 510, right: showStatTiles.value ? 240 : 40, bottom: showBestRow.value ? 170 : 40 }
  }
  const layout = route.meta.layout
  if (layout === 'map-left') return { top: 100, left: 510, right: 50, bottom: 50 }
  if (layout === 'map-right') return { top: 100, left: 110, right: 530, bottom: 50 }
  return { top: 100, left: 110, right: 50, bottom: 50 }
})

// --- layers -----------------------------------------------------------------

function setData(id: string, data: FC | FeatureCollection | null) {
  ;(map.value?.getSource(id) as GeoJSONSource | undefined)?.setData((data ?? EMPTY) as FeatureCollection)
}

function paint() {
  const m = map.value
  if (!m?.getLayer('hex')) return
  const ramp = SEQUENTIAL[theme.value]
  const [lo, hi] = hexDomain.value
  m.setPaintProperty('hex', 'fill-extrusion-color', ['interpolate', ['linear'], ['get', 'value'], ...rampStops(ramp, [lo, hi])])
  m.setPaintProperty('hex', 'fill-extrusion-height', ['interpolate', ['linear'], ['get', 'value'], lo, 60, hi, 3200])
  m.setPaintProperty('pts', 'circle-color', [
    'case', ['<', ['get', 'yield'], 0], DIVERGING[theme.value].neutral,
    ['interpolate', ['linear'], ['get', 'yield'], ...rampStops(ramp, yieldDomain.value)],
  ])
}

function visibility() {
  const m = map.value
  if (!m?.getLayer('hex')) return
  const mode = stage.mode
  const vis = (id: string, on: boolean) => m.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none')
  // Listing: no hex — translucent columns at street zoom read as ghost towers.
  vis('hex', mode === 'home' || mode === 'overview')
  vis('hex-hover', mode === 'home')
  m.setPaintProperty('hex', 'fill-extrusion-opacity', mode === 'overview' ? 0.55 : 0.9)
  vis('pts', mode === 'explore' || mode === 'overview')
  vis('pts-hl', mode === 'explore' || mode === 'overview')
  vis('comps', mode === 'listing')
  vis('comps-hl', mode === 'listing')
}

function addLayers() {
  const m = map.value!
  const mode = theme.value
  tintBasemap(m, mode)
  const source = (id: string, data: FC | FeatureCollection | null) => {
    if (!m.getSource(id)) m.addSource(id, { type: 'geojson', data: (data ?? EMPTY) as FeatureCollection })
    else setData(id, data)
  }
  source('hexes', hexes.value)
  source('pts', pts.value)
  source('comps', comps.value)
  if (!m.getLayer('hex')) {
    const ramp = SEQUENTIAL[mode]
    m.addLayer({
      id: 'hex', type: 'fill-extrusion', source: 'hexes',
      paint: { 'fill-extrusion-color': ramp[0], 'fill-extrusion-height': 0, 'fill-extrusion-base': 0, 'fill-extrusion-opacity': 0.9, 'fill-extrusion-vertical-gradient': true },
    })
    m.addLayer({ id: 'hex-hover', type: 'line', source: 'hexes', paint: { 'line-color': HOVER[mode], 'line-width': 1.5 }, filter: ['==', ['get', 'cell'], ''] })
    m.addLayer({
      id: 'pts', type: 'circle', source: 'pts',
      paint: { 'circle-radius': 5.5, 'circle-color': ramp[2], 'circle-stroke-width': 1.5, 'circle-stroke-color': STROKE[mode] },
    })
    m.addLayer({
      id: 'pts-hl', type: 'circle', source: 'pts', filter: ['==', ['get', 'id'], stage.highlightId ?? -1],
      paint: { 'circle-radius': 10, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-width': 2.5, 'circle-stroke-color': HOVER[mode] },
    })
    m.addLayer({
      id: 'comps', type: 'circle', source: 'comps',
      paint: {
        'circle-radius': ['case', ['==', ['get', 'kind'], 'subject'], 9, 6],
        'circle-color': ['case', ['==', ['get', 'kind'], 'subject'], MARKERS[mode].subject, MARKERS[mode].comp],
        'circle-stroke-width': 2,
        'circle-stroke-color': STROKE[mode],
      },
    })
    m.addLayer({
      id: 'comps-hl', type: 'circle', source: 'comps', filter: ['==', ['get', 'id'], stage.highlightComp ?? -2],
      paint: { 'circle-radius': 11, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-width': 2.5, 'circle-stroke-color': HOVER[mode] },
    })
  }
  paint()
  visibility()
}

// --- camera -----------------------------------------------------------------

let frame = 0
let idleTimer: ReturnType<typeof setTimeout> | undefined
let orbitTimer: ReturnType<typeof setTimeout> | undefined
let orbiting = false

function orbit() {
  if (!orbiting || !map.value) return
  map.value.setBearing(map.value.getBearing() + 0.04)
  frame = requestAnimationFrame(orbit)
}
function startOrbit() {
  if (prefersReducedMotion() || orbiting || !(stage.mode === 'home' || stage.mode === 'overview')) return
  orbiting = true
  frame = requestAnimationFrame(orbit)
}
function stopOrbit() {
  orbiting = false
  cancelAnimationFrame(frame)
  clearTimeout(idleTimer)
  clearTimeout(orbitTimer)
}
function pauseOrbit() {
  stopOrbit()
  idleTimer = setTimeout(startOrbit, 10_000)
}

function bounds(coords: number[][]): [[number, number], [number, number]] | null {
  if (!coords.length) return null
  let [w, s, e, n] = [180, 90, -180, -90]
  for (const [x, y] of coords) {
    w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y)
  }
  return [[w, s], [e, n]]
}

function apply() {
  const m = map.value
  if (!m || !loaded.value) return
  stopOrbit()
  const pad = fitPadding(m, padding.value)
  const still = prefersReducedMotion()
  const mode = stage.mode
  if (mode === 'listing') {
    const s = stage.subject
    if (!s) return
    m.flyTo({ center: [s.longitude, s.latitude], zoom: stage.zoom, pitch: 48, bearing: -12, padding: pad, duration: still ? 0 : 1400 })
    return
  }
  if (mode === 'explore') {
    const b = stage.bbox
    const box = b ? bounds([[b[0], b[1]], [b[2], b[3]]]) : bounds(pts.value.features.map((f) => (f.geometry as Point).coordinates))
    if (box) m.fitBounds(box, { padding: pad, pitch: 0, bearing: 0, duration: still ? 0 : 1200, maxZoom: 14.5 })
    return
  }
  const rings = hexes.value?.features.flatMap((f) => f.geometry.coordinates[0]) ?? []
  const box = bounds(rings)
  if (!box) return
  m.fitBounds(box, { padding: pad, pitch: 58, bearing: m.getBearing() || -20, duration: still ? 0 : 1200, maxZoom: 12.8 })
  orbitTimer = setTimeout(startOrbit, still ? 0 : 1300)
}

/** Coalesce the several watchers that change in one tick into a single camera move. */
let applyQueued = false
function queueApply() {
  if (applyQueued) return
  applyQueued = true
  requestAnimationFrame(() => {
    applyQueued = false
    apply()
  })
}

// --- neighbourhood labels (HTML markers need no basemap glyphs) ---------------

let markers: Marker[] = []
function drawLabels() {
  markers.forEach((mk) => mk.remove())
  markers = []
  const m = map.value
  if (!m || isPhone.value || stage.mode === 'listing') return
  markers = (communities.value?.items ?? []).flatMap((c) => {
    if (c.latitude === null || c.longitude === null) return []
    const el = document.createElement('div')
    el.className = 'pointer-events-none select-none whitespace-nowrap text-[11px] font-medium tracking-[0.02em] text-text-2 [text-shadow:0_1px_6px_var(--bg),0_0_2px_var(--bg)]'
    el.textContent = c.name
    return [new Marker({ element: el, anchor: 'center' }).setLngLat([c.longitude, c.latitude]).addTo(m)]
  })
}

// --- lifecycle ----------------------------------------------------------------

let resizeObserver: ResizeObserver | undefined

onMounted(() => {
  const market = cities.market
  const m = createMap(container.value!, theme.value, {
    center: market?.longitude && market.latitude ? [market.longitude, market.latitude] : [-79.39, 43.69],
    zoom: 10.8,
    pitch: 58,
    bearing: -20,
    maxPitch: 75,
  })
  map.value = m
  if (import.meta.env.DEV || import.meta.env.VITE_E2E) Object.assign(window, { __hexmap: m })
  onStyle(m, addLayers)

  // MapLibre measures a container mounted before layout as 400×300; keep it in sync.
  resizeObserver = new ResizeObserver(() => m.resize())
  resizeObserver.observe(container.value!)

  for (const event of ['mousedown', 'touchstart', 'wheel', 'dragstart'] as const) m.on(event, pauseOrbit)
  m.on('load', () => {
    m.resize()
    if (!m.getLayer('hex')) addLayers()
    loaded.value = true
    drawLabels()
    apply()
  })
  m.on('dragend', () => { if (stage.mode === 'explore') moved.value = true })
  m.on('zoomend', (e) => { if (stage.mode === 'explore' && 'originalEvent' in e && e.originalEvent) moved.value = true })

  m.on('mousemove', 'hex', (e: MapLayerMouseEvent) => {
    const f = e.features?.[0]
    if (!f || stage.mode !== 'home') return
    const p = f.properties as HexFeatureProps
    m.getCanvas().style.cursor = 'pointer'
    hover.value = { x: e.point.x, y: e.point.y, props: p }
    m.setFilter('hex-hover', ['==', ['get', 'cell'], p.cell])
  })
  m.on('mouseleave', 'hex', () => {
    m.getCanvas().style.cursor = ''
    hover.value = null
    m.setFilter('hex-hover', ['==', ['get', 'cell'], ''])
  })
  m.on('click', 'hex', (e: MapLayerMouseEvent) => {
    const f = e.features?.[0]
    if (!f || stage.mode !== 'home' || f.geometry.type !== 'Polygon') return
    const ring = f.geometry.coordinates[0] as [number, number][]
    const xs = ring.map((p) => p[0])
    const ys = ring.map((p) => p[1])
    hover.value = null
    router.push({
      path: '/explore',
      query: { city: cities.city, bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)].map((v) => v.toFixed(5)).join(',') },
    })
  })
  m.on('mousemove', 'pts', (e: MapLayerMouseEvent) => {
    const id = Number(e.features?.[0]?.properties?.id)
    if (!Number.isFinite(id)) return
    m.getCanvas().style.cursor = 'pointer'
    stage.highlightId = id
  })
  m.on('mouseleave', 'pts', () => {
    m.getCanvas().style.cursor = ''
    stage.highlightId = null
  })
  m.on('click', 'pts', (e: MapLayerMouseEvent) => {
    const id = Number(e.features?.[0]?.properties?.id)
    if (Number.isFinite(id)) router.push(`/listings/${id}`)
  })
  m.on('mousemove', 'comps', (e: MapLayerMouseEvent) => {
    const p = e.features?.[0]?.properties
    if (p?.kind === 'comp') stage.highlightComp = Number(p.id)
  })
  m.on('mouseleave', 'comps', () => (stage.highlightComp = null))
})

watch(hexes, (fc) => {
  setData('hexes', fc)
  paint()
})
watch(() => points.value?.city, () => queueApply())
watch(pts, (fc) => {
  setData('pts', fc)
  paint()
  if (stage.mode === 'explore' && !moved.value) queueApply()
})
watch(comps, (fc) => setData('comps', fc))
watch(() => stage.mode, () => {
  hover.value = null
  moved.value = false
  visibility()
  drawLabels()
  queueApply()
})
watch(() => [stage.subject?.latitude, stage.subject?.longitude, stage.zoom], () => queueApply())
watch(() => stage.bbox?.join(','), () => {
  moved.value = false
  queueApply()
})
watch(() => JSON.stringify(padding.value), () => queueApply())
watch(() => stage.highlightId, (id) => map.value?.getLayer('pts-hl') && map.value.setFilter('pts-hl', ['==', ['get', 'id'], id ?? -1]))
watch(() => stage.highlightComp, (id) => map.value?.getLayer('comps-hl') && map.value.setFilter('comps-hl', ['==', ['get', 'id'], id ?? -2]))
watch([communities, isPhone], drawLabels)
watch(theme, (mode) => map.value?.setStyle(styleFor(mode), { diff: false }))

onBeforeUnmount(() => {
  stopOrbit()
  resizeObserver?.disconnect()
  markers.forEach((mk) => mk.remove())
  map.value?.remove()
})

function searchHere() {
  const b = map.value!.getBounds()
  moved.value = false
  stage.areaRequest = [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]
}

const fmt = (key: HexMetric, value: number | null) => (value === null ? '—' : HEX_METRICS[key].format(value))
const ariaLabel = computed(() =>
  stage.mode === 'home' || stage.mode === 'overview'
    ? `3D map of ${HEX_METRICS[stage.metric].label.toLowerCase()} by area in ${cities.city}`
    : stage.mode === 'explore'
      ? 'Map of the listed properties, coloured by gross yield'
      : `Map of this property and ${stage.comps.length} comparable listings`,
)
</script>

<template>
  <div class="fixed inset-0 z-0 bg-bg">
    <!-- MapLibre forces position:relative on its container, so size it with h/w-full -->
    <div ref="container" class="h-full w-full" role="img" :aria-label="ariaLabel" />
    <div v-if="stage.mode === 'overview'" class="pointer-events-none absolute inset-0 bg-[var(--scrim)]" />

    <div
      v-if="hover"
      class="glass pointer-events-none absolute z-30 min-w-[190px] rounded-[14px] px-3 py-2.5 text-xs"
      :style="{ left: `${hover.x + 16}px`, top: `${hover.y + 16}px` }"
    >
      <p class="mb-1.5 text-text-2">{{ hover.props.count }} listing{{ hover.props.count === 1 ? '' : 's' }} in this area</p>
      <dl class="grid grid-cols-[auto_auto] gap-x-[18px] gap-y-[3px]">
        <template v-for="key in (Object.keys(HEX_METRICS) as HexMetric[])" :key="key">
          <dt :class="key === stage.metric ? 'text-text' : 'text-muted'">{{ HEX_METRICS[key].short }}</dt>
          <dd class="num text-right text-text">{{ fmt(key, hover.props[key]) }}</dd>
        </template>
      </dl>
      <p class="mt-2 text-[11px] text-accent">Click to see these listings</p>
    </div>

    <button
      v-if="moved && stage.mode === 'explore'"
      class="glass absolute top-[76px] z-10 -translate-x-1/2 rounded-full px-4 py-1.5 text-xs font-medium hover:text-accent"
      :class="isPhone ? 'left-1/2' : 'left-[calc(50%+244px)]'"
      @click="searchHere"
    >
      Search this area
    </button>

    <div
      v-if="basemapFailed"
      class="absolute z-[5] rounded-[10px] border border-border bg-panel px-2.5 py-1.5 text-[11px] text-warn"
      :class="isPhone ? 'right-3 top-[76px]' : 'bottom-3 right-3'"
      role="status"
    >
      Basemap unreachable — showing data only
    </div>
  </div>
</template>
