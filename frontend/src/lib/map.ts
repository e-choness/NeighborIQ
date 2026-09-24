/**
 * MapLibre setup shared by every map in the app.
 *
 * Basemap: a self-hosted Protomaps PMTiles file (VITE_PMTILES_URL), styled
 * from src/theme/palette.ts. Without it the map renders data layers on the
 * plain theme background — useful offline and in tests.
 */
import { layers } from '@protomaps/basemaps'
import { addProtocol, Map as MapLibreMap, setWorkerUrl, type MapOptions, type StyleSpecification } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Protocol } from 'pmtiles'
import { basemapFlavor, SURFACE, type Mode } from '@/theme/palette'

const PMTILES_URL = import.meta.env.VITE_PMTILES_URL as string | undefined
const GLYPHS =
  (import.meta.env.VITE_MAP_GLYPHS as string | undefined) ??
  'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf'
const SPRITE_BASE =
  (import.meta.env.VITE_MAP_SPRITE as string | undefined) ?? 'https://protomaps.github.io/basemaps-assets/sprites/v4'

// MapLibre 6 ships its worker as a separate ES module; let Vite bundle it.
setWorkerUrl(workerUrl)

let protocolRegistered = false
export const hasBasemap = Boolean(PMTILES_URL)

export function styleFor(mode: Mode): StyleSpecification {
  if (!PMTILES_URL) {
    return {
      version: 8,
      sources: {},
      layers: [{ id: 'background', type: 'background', paint: { 'background-color': SURFACE[mode] } }],
    }
  }
  if (!protocolRegistered) {
    addProtocol('pmtiles', new Protocol().tile)
    protocolRegistered = true
  }
  return {
    version: 8,
    glyphs: GLYPHS,
    sprite: `${SPRITE_BASE}/${mode === 'dark' ? 'dark' : 'light'}`,
    sources: {
      protomaps: {
        type: 'vector',
        url: `pmtiles://${PMTILES_URL}`,
        attribution: '© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors · Protomaps',
      },
    },
    layers: layers('protomaps', basemapFlavor(mode), { lang: 'en' }),
  }
}

export function createMap(
  container: HTMLElement,
  mode: Mode,
  options: Partial<MapOptions> = {},
): MapLibreMap {
  return new MapLibreMap({
    container,
    style: styleFor(mode),
    center: [-79.39, 43.66],
    zoom: 11,
    attributionControl: { compact: true },
    ...options,
  })
}

/** Run `add` now if the style is loaded, and again after every setStyle (theme change). */
export function onStyle(map: MapLibreMap, add: () => void) {
  if (map.isStyleLoaded()) add()
  map.on('style.load', add)
  return () => map.off('style.load', add)
}

/** Colour stops for an interpolate expression over [lo, hi]. */
export function rampStops(colors: string[], [lo, hi]: [number, number]): (number | string)[] {
  return colors.flatMap((color, i) => [lo + ((hi - lo) * i) / (colors.length - 1), color])
}
