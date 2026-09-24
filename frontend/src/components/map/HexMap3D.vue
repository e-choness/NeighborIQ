<script setup lang="ts">
/**
 * 3D hexagon map: each H3 cell is extruded by the chosen metric; height and
 * colour encode the same value (redundant encoding, so colour is never the only
 * channel). The camera orbits slowly until the viewer interacts; reduced-motion
 * users get a static view.
 */
import { Marker, type GeoJSONSource, type Map as MapLibreMap, type MapLayerMouseEvent } from 'maplibre-gl'
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { aggregateHexes, domain, HEX_METRICS, type HexFeatureProps, type HexMetric } from '@/lib/hex'
import { createMap, onStyle, rampStops, styleFor } from '@/lib/map'
import { prefersReducedMotion, theme } from '@/lib/theme'
import type { MarketPoints } from '@/lib/types'
import { SEQUENTIAL } from '@/theme/palette'

const props = defineProps<{
  points: MarketPoints | null
  metric: HexMetric
  center: [number, number] | null
  /** Neighbourhood names drawn as HTML markers — context that needs no basemap fonts */
  labels?: { name: string; latitude: number; longitude: number }[]
  /** Pixels covered by overlay UI on the left, so data is framed beside it */
  padLeft?: number
}>()
const emit = defineEmits<{
  domain: [[number, number]]
  select: [bbox: [number, number, number, number]]
}>()

const container = ref<HTMLElement>()
const map = shallowRef<MapLibreMap>()
const hover = ref<{ x: number; y: number; props: HexFeatureProps } | null>(null)
let frame = 0
let idleTimer: ReturnType<typeof setTimeout> | undefined
let orbiting = false

const hexes = computed(() => (props.points ? aggregateHexes(props.points, props.metric) : null))
const valueDomain = computed<[number, number]>(() =>
  domain(hexes.value?.features.map((f) => f.properties.value) ?? []),
)
watch(valueDomain, (d) => emit('domain', d), { immediate: true })

const MAX_HEIGHT_M = 3200

function paint() {
  const m = map.value
  if (!m || !m.getLayer('hex')) return
  const [lo, hi] = valueDomain.value
  const colors = SEQUENTIAL[theme.value]
  m.setPaintProperty('hex', 'fill-extrusion-color', [
    'interpolate', ['linear'], ['get', 'value'], ...rampStops(colors, [lo, hi]),
  ])
  m.setPaintProperty('hex', 'fill-extrusion-height', [
    'interpolate', ['linear'], ['get', 'value'], lo, 60, hi, MAX_HEIGHT_M,
  ])
}

function addLayers() {
  const m = map.value!
  if (!m.getSource('hexes')) {
    m.addSource('hexes', { type: 'geojson', data: hexes.value ?? { type: 'FeatureCollection', features: [] } })
  }
  if (!m.getLayer('hex')) {
    m.addLayer({
      id: 'hex',
      type: 'fill-extrusion',
      source: 'hexes',
      paint: {
        'fill-extrusion-color': SEQUENTIAL[theme.value][0],
        'fill-extrusion-height': 0,
        'fill-extrusion-base': 0,
        'fill-extrusion-opacity': 0.9,
        'fill-extrusion-vertical-gradient': true,
      },
    })
    m.addLayer({
      id: 'hex-hover',
      type: 'line',
      source: 'hexes',
      paint: { 'line-color': theme.value === 'dark' ? '#e8eef5' : '#0b0f14', 'line-width': 1.5 },
      filter: ['==', ['get', 'cell'], ''],
    })
  }
  paint()
}

function orbit() {
  const m = map.value
  if (!m || !orbiting) return
  m.setBearing(m.getBearing() + 0.04)
  frame = requestAnimationFrame(orbit)
}

function startOrbit() {
  if (prefersReducedMotion() || orbiting) return
  orbiting = true
  frame = requestAnimationFrame(orbit)
}

function pauseOrbit() {
  orbiting = false
  cancelAnimationFrame(frame)
  clearTimeout(idleTimer)
  idleTimer = setTimeout(startOrbit, 10_000)
}

function fitToData() {
  const m = map.value
  const features = hexes.value?.features
  if (!m || !features?.length) return
  let [w, s, e, n] = [180, 90, -180, -90]
  for (const f of features) {
    for (const [x, y] of f.geometry.coordinates[0]) {
      w = Math.min(w, x); e = Math.max(e, x); s = Math.min(s, y); n = Math.max(n, y)
    }
  }
  // Desktop: the overlay sits on the left; phones: it sits at the bottom (~half the screen)
  const desktop = window.innerWidth >= 1024
  const left = desktop ? (props.padLeft ?? 0) : 0
  const bottom = desktop ? 60 : Math.round(window.innerHeight * 0.55)
  m.fitBounds([[w, s], [e, n]], {
    padding: { top: 80, bottom, right: 30, left: left + 30 },
    pitch: 58, bearing: m.getBearing(), duration: 1200, maxZoom: 12.8,
  })
}

onMounted(() => {
  const m = createMap(container.value!, theme.value, {
    pitch: 58,
    bearing: -20,
    zoom: 11.2,
    center: props.center ?? [-79.39, 43.66],
    maxPitch: 75,
  })
  map.value = m
  if (import.meta.env.DEV) Object.assign(window, { __hexmap: m })
  onStyle(m, addLayers)

  for (const event of ['mousedown', 'touchstart', 'wheel', 'dragstart'] as const) m.on(event, pauseOrbit)
  m.on('load', () => {
    fitToData()
    startOrbit()
  })

  m.on('mousemove', 'hex', (e: MapLayerMouseEvent) => {
    const f = e.features?.[0]
    if (!f) return
    m.getCanvas().style.cursor = 'pointer'
    hover.value = { x: e.point.x, y: e.point.y, props: f.properties as HexFeatureProps }
    m.setFilter('hex-hover', ['==', ['get', 'cell'], (f.properties as HexFeatureProps).cell])
  })
  m.on('mouseleave', 'hex', () => {
    m.getCanvas().style.cursor = ''
    hover.value = null
    m.setFilter('hex-hover', ['==', ['get', 'cell'], ''])
  })
  m.on('click', 'hex', (e: MapLayerMouseEvent) => {
    const f = e.features?.[0]
    if (!f || f.geometry.type !== 'Polygon') return
    const ring = f.geometry.coordinates[0] as [number, number][]
    const xs = ring.map((p) => p[0])
    const ys = ring.map((p) => p[1])
    emit('select', [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)])
  })
})

watch(hexes, (fc) => {
  const source = map.value?.getSource('hexes') as GeoJSONSource | undefined
  if (fc && source) {
    source.setData(fc)
    paint()
  }
})

watch(() => props.points?.city, () => setTimeout(fitToData, 50))

let markers: Marker[] = []
function drawLabels() {
  markers.forEach((mk) => mk.remove())
  const m = map.value
  if (!m || window.innerWidth < 640) return // too crowded on phones
  markers = (props.labels ?? []).map((l) => {
    const el = document.createElement('div')
    el.className = 'pointer-events-none select-none whitespace-nowrap text-[11px] font-medium tracking-wide text-text-2 [text-shadow:0_1px_6px_var(--surface)]'
    el.textContent = l.name
    return new Marker({ element: el, anchor: 'center' }).setLngLat([l.longitude, l.latitude]).addTo(m)
  })
}
watch(() => [props.labels, map.value], drawLabels)

watch(theme, (mode) => map.value?.setStyle(styleFor(mode), { diff: false }))

onBeforeUnmount(() => {
  markers.forEach((mk) => mk.remove())
  orbiting = false
  cancelAnimationFrame(frame)
  clearTimeout(idleTimer)
  map.value?.remove()
})

const fmt = (key: HexMetric, value: number | null) => (value === null ? '—' : HEX_METRICS[key].format(value))
</script>

<template>
  <div class="absolute inset-0">
    <!-- MapLibre forces position:relative on its container, so size it with h/w-full -->
    <div ref="container" class="h-full w-full" role="img" :aria-label="`3D map of ${HEX_METRICS[metric].label.toLowerCase()} by area`" />
    <div
      v-if="hover"
      class="glass pointer-events-none absolute z-10 min-w-44 rounded-lg px-3 py-2 text-xs shadow-xl"
      :style="{ left: `${hover.x + 14}px`, top: `${hover.y + 14}px` }"
    >
      <p class="mb-1 text-text-2">{{ hover.props.count }} listing{{ hover.props.count === 1 ? '' : 's' }} in this area</p>
      <dl class="grid grid-cols-[auto_auto] gap-x-4 gap-y-0.5">
        <template v-for="key in (Object.keys(HEX_METRICS) as HexMetric[])" :key="key">
          <dt :class="key === metric ? 'text-text' : 'text-muted'">{{ HEX_METRICS[key].short }}</dt>
          <dd class="num text-right" :class="key === metric ? 'text-text' : 'text-text-2'">{{ fmt(key, hover.props[key]) }}</dd>
        </template>
      </dl>
    </div>
  </div>
</template>
