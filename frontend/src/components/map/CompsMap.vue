<script setup lang="ts">
/** The listing and its comparables. Subject vs comp differ in size as well as colour. */
import type { Map as MapLibreMap } from 'maplibre-gl'
import { onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'
import { createMap, onStyle, styleFor } from '@/lib/map'
import { theme } from '@/lib/theme'
import type { Comp } from '@/lib/types'
import { MARKERS } from '@/theme/palette'

const props = defineProps<{ subject: { latitude: number; longitude: number }; comps: Comp[] }>()
const container = useTemplateRef<HTMLDivElement>('container')
const map = shallowRef<MapLibreMap>()

function data() {
  return {
    type: 'FeatureCollection' as const,
    features: [
      ...props.comps.map((c) => ({
        type: 'Feature' as const,
        properties: { kind: 'comp' },
        geometry: { type: 'Point' as const, coordinates: [c.longitude, c.latitude] },
      })),
      {
        type: 'Feature' as const,
        properties: { kind: 'subject' },
        geometry: { type: 'Point' as const, coordinates: [props.subject.longitude, props.subject.latitude] },
      },
    ],
  }
}

function add() {
  const m = map.value!
  const colors = MARKERS[theme.value]
  if (!m.getSource('pts')) m.addSource('pts', { type: 'geojson', data: data() })
  if (!m.getLayer('pts')) {
    m.addLayer({
      id: 'pts',
      type: 'circle',
      source: 'pts',
      paint: {
        'circle-radius': ['case', ['==', ['get', 'kind'], 'subject'], 8, 5],
        'circle-color': ['case', ['==', ['get', 'kind'], 'subject'], colors.subject, colors.comp],
        'circle-stroke-width': 2,
        'circle-stroke-color': theme.value === 'dark' ? '#0b0f14' : '#ffffff',
      },
    })
  }
}

function fit() {
  const m = map.value
  if (!m) return
  const xs = [props.subject.longitude, ...props.comps.map((c) => c.longitude)]
  const ys = [props.subject.latitude, ...props.comps.map((c) => c.latitude)]
  m.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]], { padding: 36, maxZoom: 15, duration: 0 })
}

onMounted(() => {
  map.value = createMap(container.value!, theme.value, {
    center: [props.subject.longitude, props.subject.latitude],
    zoom: 13,
    cooperativeGestures: true,
  })
  onStyle(map.value, add)
  map.value.on('load', fit)
})
watch(theme, (mode) => map.value?.setStyle(styleFor(mode), { diff: false }))
onBeforeUnmount(() => map.value?.remove())
</script>

<template>
  <div class="relative overflow-hidden rounded-xl border border-border">
    <div ref="container" class="h-56 w-full" role="img" :aria-label="`Map of this listing and ${comps.length} comparable listings`" />
    <div class="glass absolute bottom-2 left-2 flex gap-3 rounded-md px-2 py-1 text-[11px] text-text-2">
      <span class="flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-full" :style="{ background: MARKERS[theme].subject }" />This listing</span>
      <span class="flex items-center gap-1.5"><span class="h-2 w-2 rounded-full" :style="{ background: MARKERS[theme].comp }" />Comparable</span>
    </div>
  </div>
</template>
