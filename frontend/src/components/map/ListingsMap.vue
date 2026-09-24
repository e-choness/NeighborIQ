<script setup lang="ts">
/**
 * Listing dots coloured by gross yield (sequential), with the hovered row
 * highlighted. Emits the viewport when the user wants to search there.
 */
import { Marker, type GeoJSONSource, type Map as MapLibreMap, type MapLayerMouseEvent } from 'maplibre-gl'
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, useTemplateRef, watch } from 'vue'
import { domain } from '@/lib/hex'
import { createMap, onStyle, rampStops, styleFor } from '@/lib/map'
import { theme } from '@/lib/theme'
import type { Listing } from '@/lib/types'
import { SEQUENTIAL } from '@/theme/palette'
import { pct } from '@/lib/format'

const props = defineProps<{
  listings: Listing[]
  highlight: number | null
  bbox?: [number, number, number, number] | null
  labels?: { name: string; latitude: number; longitude: number }[]
}>()
const emit = defineEmits<{ hover: [number | null]; open: [number]; searchArea: [[number, number, number, number]] }>()

const container = useTemplateRef<HTMLDivElement>('container')
const map = shallowRef<MapLibreMap>()
const moved = ref(false)

const geojson = computed(() => ({
  type: 'FeatureCollection' as const,
  features: props.listings
    .filter((l) => l.latitude !== null && l.longitude !== null)
    .map((l) => ({
      type: 'Feature' as const,
      id: l.id,
      properties: { id: l.id, yield: l.gross_yield_pct ?? -1 },
      geometry: { type: 'Point' as const, coordinates: [l.longitude!, l.latitude!] },
    })),
}))
const yieldDomain = computed(() => domain(props.listings.flatMap((l) => (l.gross_yield_pct === null ? [] : [l.gross_yield_pct]))))

function paint() {
  const m = map.value
  if (!m?.getLayer('dots')) return
  m.setPaintProperty('dots', 'circle-color', [
    'case', ['<', ['get', 'yield'], 0], theme.value === 'dark' ? '#3a4452' : '#c9cfd6',
    ['interpolate', ['linear'], ['get', 'yield'], ...rampStops(SEQUENTIAL[theme.value], yieldDomain.value)],
  ])
}

function add() {
  const m = map.value!
  if (!m.getSource('listings')) m.addSource('listings', { type: 'geojson', data: geojson.value })
  if (!m.getLayer('dots')) {
    m.addLayer({
      id: 'dots',
      type: 'circle',
      source: 'listings',
      paint: {
        'circle-radius': ['case', ['boolean', ['feature-state', 'hover'], false], 9, 5.5],
        'circle-color': SEQUENTIAL[theme.value][2],
        'circle-stroke-width': ['case', ['boolean', ['feature-state', 'hover'], false], 2.5, 1.5],
        'circle-stroke-color': theme.value === 'dark' ? '#0b0f14' : '#ffffff',
      },
    })
  }
  paint()
}

function fit() {
  const m = map.value
  if (!m) return
  if (props.bbox) {
    m.fitBounds([[props.bbox[0], props.bbox[1]], [props.bbox[2], props.bbox[3]]], { padding: 60, duration: 0, maxZoom: 15 })
    return
  }
  const coords = geojson.value.features.map((f) => f.geometry.coordinates)
  if (!coords.length) return
  const xs = coords.map((c) => c[0])
  const ys = coords.map((c) => c[1])
  m.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]], { padding: 48, duration: 400, maxZoom: 14 })
}

let lastHover: number | null = null
function setHover(id: number | null) {
  const m = map.value
  if (!m?.getSource('listings')) return
  if (lastHover !== null) m.setFeatureState({ source: 'listings', id: lastHover }, { hover: false })
  if (id !== null) m.setFeatureState({ source: 'listings', id }, { hover: true })
  lastHover = id
}

onMounted(() => {
  const m = createMap(container.value!, theme.value, { zoom: 11 })
  map.value = m
  onStyle(m, add)
  m.on('load', fit)
  m.on('dragend', () => (moved.value = true))
  m.on('zoomend', (e) => { if ('originalEvent' in e && e.originalEvent) moved.value = true })
  m.on('mousemove', 'dots', (e: MapLayerMouseEvent) => {
    m.getCanvas().style.cursor = 'pointer'
    emit('hover', Number(e.features?.[0]?.properties?.id))
  })
  m.on('mouseleave', 'dots', () => {
    m.getCanvas().style.cursor = ''
    emit('hover', null)
  })
  m.on('click', 'dots', (e: MapLayerMouseEvent) => emit('open', Number(e.features?.[0]?.properties?.id)))
})

watch(geojson, (fc) => {
  ;(map.value?.getSource('listings') as GeoJSONSource | undefined)?.setData(fc)
  paint()
  if (!moved.value) fit()
})
watch(() => props.highlight, setHover)

let markers: Marker[] = []
watch(() => [props.labels, map.value] as const, () => {
  markers.forEach((mk) => mk.remove())
  const m = map.value
  if (!m) return
  markers = (props.labels ?? []).map((l) => {
    const el = document.createElement('div')
    el.className = 'pointer-events-none select-none whitespace-nowrap text-[11px] font-medium text-muted [text-shadow:0_1px_6px_var(--surface)]'
    el.textContent = l.name
    return new Marker({ element: el }).setLngLat([l.longitude, l.latitude]).addTo(m)
  })
})
watch(theme, (mode) => map.value?.setStyle(styleFor(mode), { diff: false }))
onBeforeUnmount(() => {
  markers.forEach((mk) => mk.remove())
  map.value?.remove()
})

function searchHere() {
  const b = map.value!.getBounds()
  moved.value = false
  emit('searchArea', [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()])
}
</script>

<template>
  <div class="absolute inset-0">
    <div ref="container" class="h-full w-full" role="img" aria-label="Map of the listed properties, coloured by gross yield" />
    <div class="glass absolute bottom-3 left-3 w-52 rounded-lg px-3 py-2 text-[11px]" aria-hidden="true">
      <p class="mb-1.5 text-text-2">Dot colour · gross yield</p>
      <div class="h-1.5 rounded-full" :style="{ background: `linear-gradient(90deg, ${SEQUENTIAL[theme].join(', ')})` }" />
      <div class="num mt-1 flex justify-between text-muted"><span>{{ pct(yieldDomain[0]) }}</span><span>{{ pct(yieldDomain[1]) }}</span></div>
    </div>
    <button
      v-if="moved"
      class="glass absolute left-1/2 top-4 -translate-x-1/2 rounded-full px-4 py-1.5 text-xs font-medium shadow-lg hover:text-accent"
      @click="searchHere"
    >
      Search this area
    </button>
  </div>
</template>
