/**
 * MapLibre setup shared by every map in the app.
 *
 * Basemap, in order of preference:
 *   1. a self-hosted Protomaps PMTiles file (VITE_PMTILES_URL), styled from src/theme/palette.ts;
 *   2. a hosted vector style (VITE_BASEMAP=hosted, the default — OpenFreeMap), tinted to the palette;
 *   3. none (VITE_BASEMAP=none): data layers on the plain theme background — useful offline and in tests.
 * If a hosted style has not loaded 12 s after the map is created, the map falls back to (3)
 * and `basemapFailed` becomes true so the UI can say so.
 */
import { layers } from '@protomaps/basemaps'
import { addProtocol, Map as MapLibreMap, setWorkerUrl, type MapOptions, type StyleSpecification } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Protocol } from 'pmtiles'
import { ref } from 'vue'
import { BASEMAP_TINT, basemapFlavor, SURFACE, type Mode } from '@/theme/palette'

const PMTILES_URL = import.meta.env.VITE_PMTILES_URL as string | undefined
const GLYPHS =
  (import.meta.env.VITE_MAP_GLYPHS as string | undefined) ??
  'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf'
const SPRITE_BASE =
  (import.meta.env.VITE_MAP_SPRITE as string | undefined) ?? 'https://protomaps.github.io/basemaps-assets/sprites/v4'
const HOSTED: Record<Mode, string> = {
  dark: import.meta.env.VITE_BASEMAP_STYLE_DARK || 'https://tiles.openfreemap.org/styles/dark',
  light: import.meta.env.VITE_BASEMAP_STYLE_LIGHT || 'https://tiles.openfreemap.org/styles/positron',
}
const STYLE_TIMEOUT_MS = 12_000

export type BasemapKind = 'hosted' | 'pmtiles' | 'none'

function resolveBasemap(): BasemapKind {
  if (PMTILES_URL) return 'pmtiles'
  const requested = import.meta.env.VITE_BASEMAP
  return requested === 'none' || requested === 'pmtiles' ? 'none' : 'hosted'
}

// MapLibre 6 ships its worker as a separate ES module; let Vite bundle it.
setWorkerUrl(workerUrl)

let protocolRegistered = false
/** The basemap in use; drops to 'none' if the hosted style is unreachable. */
let basemap: BasemapKind = resolveBasemap()
/** True once a hosted basemap failed to load and the app fell back to data only. */
export const basemapFailed = ref(false)

export const hasBasemap = () => basemap !== 'none'

function backgroundOnly(mode: Mode): StyleSpecification {
  return {
    version: 8,
    sources: {},
    layers: [{ id: 'background', type: 'background', paint: { 'background-color': SURFACE[mode] } }],
  }
}

export function styleFor(mode: Mode): StyleSpecification | string {
  if (basemap === 'hosted') return HOSTED[mode]
  if (basemap === 'none') return backgroundOnly(mode)
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

/**
 * Pull a hosted style towards the app palette: ground and water from BASEMAP_TINT, parks and
 * landcover faded. Layer ids differ between hosted styles and versions, so this is best effort.
 */
export function tintBasemap(map: MapLibreMap, mode: Mode) {
  if (basemap !== 'hosted') return
  const tint = BASEMAP_TINT[mode]
  try {
    for (const layer of map.getStyle().layers) {
      if (layer.type === 'background') map.setPaintProperty(layer.id, 'background-color', tint.earth)
      else if (layer.type === 'fill' && /water/.test(layer.id)) map.setPaintProperty(layer.id, 'fill-color', tint.water)
      else if (layer.type === 'fill' && /landuse|park|landcover|wood|grass/.test(layer.id)) {
        map.setPaintProperty(layer.id, 'fill-opacity', 0.35)
      }
    }
  } catch {
    /* hosted style changed shape — leave it untinted */
  }
}

export function createMap(
  container: HTMLElement,
  mode: Mode,
  options: Partial<MapOptions> = {},
): MapLibreMap {
  const map = new MapLibreMap({
    container,
    style: styleFor(mode),
    center: [-79.39, 43.66],
    zoom: 11,
    attributionControl: { compact: true },
    ...options,
  })

  // Hosted styles reference sprite images that are not always present (e.g. `wood-pattern`).
  map.on('styleimagemissing', (e) => {
    if (!map.hasImage(e.id)) map.addImage(e.id, { width: 1, height: 1, data: new Uint8Array(4) })
  })

  // Fall back to data only when the hosted style JSON never arrives. Checks for the style
  // event rather than isStyleLoaded(), which stays false while tiles are still loading.
  if (basemap === 'hosted') {
    let styleArrived = false
    const arrived = () => (styleArrived = true)
    map.once('styledata', arrived)
    map.once('style.load', arrived)
    const timer = setTimeout(() => {
      if (styleArrived || basemap !== 'hosted') return
      basemap = 'none'
      basemapFailed.value = true
      map.setStyle(backgroundOnly(mode), { diff: false })
      map.getContainer().dispatchEvent(new CustomEvent('basemap-failed', { bubbles: true }))
    }, STYLE_TIMEOUT_MS)
    map.once('remove', () => clearTimeout(timer))
  }
  return map
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

/**
 * Shrink opposing paddings proportionally so at least `room` px of map remains; otherwise
 * short windows log "Map cannot fit within canvas" and skip the fit.
 */
export function fitPadding(
  map: MapLibreMap,
  padding: { top: number; bottom: number; left: number; right: number },
  room = 120,
) {
  const el = map.getContainer()
  const out = { ...padding }
  const shrink = (a: 'top' | 'left', b: 'bottom' | 'right', size: number) => {
    const over = out[a] + out[b] + room - size
    if (over <= 0) return
    const total = out[a] + out[b] || 1
    out[a] = Math.max(0, out[a] - (over * out[a]) / total)
    out[b] = Math.max(0, out[b] - (over * out[b]) / total)
  }
  shrink('top', 'bottom', el.clientHeight)
  shrink('left', 'right', el.clientWidth)
  return out
}
