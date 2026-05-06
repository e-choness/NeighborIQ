<template>
  <div class="relative w-full h-full bg-slate-900" ref="mapContainer">
    <!-- Map renders here -->
    <div ref="mapEl" class="w-full h-full"></div>

    <!-- Map controls overlay -->
    <div class="absolute top-3 right-3 flex flex-col gap-2 z-10">
      <button
        @click="zoomIn"
        class="w-8 h-8 bg-slate-800/90 backdrop-blur border border-slate-700 rounded-lg flex items-center justify-center text-white hover:bg-slate-700 transition-colors"
        title="Zoom in"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
      </button>
      <button
        @click="zoomOut"
        class="w-8 h-8 bg-slate-800/90 backdrop-blur border border-slate-700 rounded-lg flex items-center justify-center text-white hover:bg-slate-700 transition-colors"
        title="Zoom out"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
        </svg>
      </button>
      <button
        @click="resetView"
        class="w-8 h-8 bg-slate-800/90 backdrop-blur border border-slate-700 rounded-lg flex items-center justify-center text-white hover:bg-slate-700 transition-colors"
        title="Reset view"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>
    </div>

    <!-- Marker count badge -->
    <div
      v-if="houses.length > 0"
      class="absolute bottom-3 left-3 px-3 py-1.5 bg-slate-800/90 backdrop-blur border border-slate-700 rounded-lg text-xs text-slate-300 z-10"
    >
      {{ houses.length }} listing{{ houses.length !== 1 ? 's' : '' }} on map
    </div>

    <!-- No data state -->
    <div
      v-if="houses.length === 0 && !loading"
      class="absolute inset-0 flex items-center justify-center pointer-events-none"
    >
      <div class="text-center">
        <svg class="w-10 h-10 text-slate-600 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <p class="text-xs text-slate-500">No properties with coordinates</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import type Map from 'ol/Map'
import type Feature from 'ol/Feature'
import type { Geometry } from 'ol/geom'
import type VectorSource from 'ol/source/Vector'
import type VectorLayer from 'ol/layer/Vector'
import type { MapBrowserEvent } from 'ol'
import type { FeatureLike } from 'ol/Feature'
import type { House } from '@/types'

const props = defineProps<{
  houses: House[]
  selectedHouse?: House | null
  loading?: boolean
}>()

const emit = defineEmits<{
  'select-house': [house: House]
}>()

interface OLModules {
  ol: typeof import('ol')
  olLayer: typeof import('ol/layer')
  olSource: typeof import('ol/source')
  olProj: typeof import('ol/proj')
  olStyle: typeof import('ol/style')
  olGeom: typeof import('ol/geom')
  olFeature: typeof import('ol/Feature')
}

const mapEl = ref<HTMLElement | null>(null)
let map: Map | null = null
let markerLayer: {
  vectorSource: VectorSource<Feature<Geometry>>
  clusterLayer: VectorLayer<Feature<Geometry>>
} | null = null
let olModule: OLModules | null = null

// Default center: Canada (Toronto area)
const DEFAULT_CENTER = [-79.3832, 43.6532] // [lon, lat]
const DEFAULT_ZOOM = 11

async function initMap() {
  if (!mapEl.value) return

  // Dynamic import of OpenLayers (avoids SSR issues)
  const ol = await import('ol')
  const olLayer = await import('ol/layer')
  const olSource = await import('ol/source')
  const olProj = await import('ol/proj')
  const olStyle = await import('ol/style')
  const olGeom = await import('ol/geom')
  const olFeature = await import('ol/Feature')

  olModule = { ol, olLayer, olSource, olProj, olStyle, olGeom, olFeature }

  // Create tile layer with CartoDB dark tiles; crossOrigin required for CORS
  const tileLayer = new olLayer.Tile({
    source: new olSource.OSM({
      url: 'https://{a-c}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      attributions: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
      crossOrigin: 'anonymous',
    }),
  })

  // Create vector source for markers
  const vectorSource = new olSource.Vector()

  // Cluster source for performance
  const clusterSource = new olSource.Cluster({
    distance: 40,
    source: vectorSource,
  })

  // Cluster style function
  const clusterLayer = new olLayer.Vector({
    source: clusterSource,
    style: (feature: FeatureLike) => {
      const size = (feature.get('features') as FeatureLike[]).length
      if (size === 1) {
        // Single marker
        return new olStyle.Style({
          image: new olStyle.Circle({
            radius: 8,
            fill: new olStyle.Fill({ color: '#8B5CF6' }),
            stroke: new olStyle.Stroke({ color: '#ffffff', width: 2 }),
          }),
        })
      }
      // Cluster marker
      return new olStyle.Style({
        image: new olStyle.Circle({
          radius: 14,
          fill: new olStyle.Fill({ color: '#7C3AED' }),
          stroke: new olStyle.Stroke({ color: '#ffffff', width: 2 }),
        }),
        text: new olStyle.Text({
          text: size.toString(),
          fill: new olStyle.Fill({ color: '#ffffff' }),
          font: 'bold 11px Inter, sans-serif',
        }),
      })
    },
  })

  markerLayer = { vectorSource, clusterLayer }

  // Create map
  map = new ol.Map({
    target: mapEl.value,
    layers: [tileLayer, clusterLayer],
    view: new ol.View({
      center: olProj.fromLonLat(DEFAULT_CENTER),
      zoom: DEFAULT_ZOOM,
    }),
    controls: [], // we have custom controls
  })

  // Click handler
  map.on('click', (evt: MapBrowserEvent<MouseEvent>) => {
    map!.forEachFeatureAtPixel(evt.pixel, (feature: FeatureLike) => {
      const features = feature.get('features') as FeatureLike[] | undefined
      if (features && features.length === 1) {
        const house = features[0].get('house') as House | undefined
        if (house) emit('select-house', house)
      }
    })
  })

  // Cursor pointer on hover
  map.on('pointermove', (evt: MapBrowserEvent<MouseEvent>) => {
    const hit = map!.hasFeatureAtPixel(evt.pixel)
    if (mapEl.value) {
      mapEl.value.style.cursor = hit ? 'pointer' : ''
    }
  })

  // Initial marker population
  updateMarkers()
}

function updateMarkers() {
  if (!markerLayer || !olModule) return
  const { olProj, olGeom, olFeature } = olModule

  markerLayer.vectorSource.clear()

  const features = props.houses
    .filter((h) => h.latitude !== null && h.longitude !== null)
    .map((h) => {
      const feature = new olFeature.default({
        geometry: new olGeom.Point(olProj.fromLonLat([h.longitude!, h.latitude!])),
      })
      feature.set('house', h)
      return feature
    })

  markerLayer.vectorSource.addFeatures(features)
}

function zoomIn() {
  if (!map) return
  const view = map.getView()
  view.setZoom((view.getZoom() || DEFAULT_ZOOM) + 1)
}

function zoomOut() {
  if (!map) return
  const view = map.getView()
  view.setZoom((view.getZoom() || DEFAULT_ZOOM) - 1)
}

function resetView() {
  if (!map || !olModule) return
  map.getView().setCenter(olModule.olProj.fromLonLat(DEFAULT_CENTER))
  map.getView().setZoom(DEFAULT_ZOOM)
}

watch(() => props.houses, updateMarkers, { deep: true })

watch(() => props.selectedHouse, (house) => {
  if (!house || !map || !olModule || house.latitude === null || house.longitude === null) return
  const center = olModule.olProj.fromLonLat([house.longitude, house.latitude])
  map.getView().animate({ center, zoom: 15, duration: 400 })
})

onMounted(initMap)

onUnmounted(() => {
  if (map) {
    map.setTarget(undefined)
    map = null
  }
})
</script>

<style>
/* OpenLayers base styles must be global */
.ol-viewport {
  touch-action: pan-y;
}
</style>
