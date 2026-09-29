/**
 * Map and data colours — the single place to change them.
 *
 * The basemap (Protomaps flavor or hosted-style tint) and every data layer read from here.
 * The data ramps were validated for step visibility, colour-vision deficiency separation and
 * contrast against the basemap ground — re-run `node scripts/check-palette.mjs`
 * (docs/frontend/overview.md#colour) after changing them.
 */
import { namedFlavor, type Flavor } from '@protomaps/basemaps'

export type Mode = 'dark' | 'light'

/** Self-hosted PMTiles basemap: low-contrast ground so data layers carry the contrast. */
export const BASEMAP: Record<Mode, Partial<Flavor>> = {
  dark: {
    background: '#090c0b',
    earth: '#0c100f',
    water: '#050807',
    park_a: '#0f1714', park_b: '#0f1714', wood_a: '#0f1714', wood_b: '#0f1714',
    buildings: '#131a17',
    minor_a: '#171f1c', minor_b: '#171f1c', minor_service: '#141b18', other: '#141b18',
    link: '#1c2622', major: '#212d28', highway: '#293832', railway: '#1c2622',
    boundaries: '#2e3c36',
    roads_label_minor: '#5c6a63', roads_label_major: '#737f79',
    roads_label_minor_halo: '#090c0b', roads_label_major_halo: '#090c0b',
    subplace_label: '#7d8a83', subplace_label_halo: '#090c0b',
    city_label: '#aab6af', city_label_halo: '#090c0b',
  },
  light: {
    background: '#e9eeeb',
    earth: '#eef2ef',
    water: '#cfdbd5',
    park_a: '#e1eae3', park_b: '#e1eae3', wood_a: '#e1eae3', wood_b: '#e1eae3',
    buildings: '#e0e6e2',
    minor_a: '#ffffff', minor_b: '#ffffff', major: '#ffffff', highway: '#f7f9f8',
  },
}

/** Hosted basemap tint (OpenFreeMap styles): ground and water pulled to the glass palette. */
export const BASEMAP_TINT: Record<Mode, { earth: string; water: string }> = {
  dark: { earth: BASEMAP.dark.earth!, water: BASEMAP.dark.water! },
  light: { earth: BASEMAP.light.earth!, water: BASEMAP.light.water! },
}

export function basemapFlavor(mode: Mode): Flavor {
  return { ...namedFlavor(mode === 'dark' ? 'dark' : 'light'), ...BASEMAP[mode] }
}

/** Sequential magnitude (one hue, sage): low → high. Validated as ordinal ramps. */
export const SEQUENTIAL: Record<Mode, string[]> = {
  dark: ['#1d3a2e', '#2a5140', '#3b6a53', '#548868', '#7aab86', '#b3d7b8'],
  light: ['#c3dcc8', '#8fb698', '#5f8a6c', '#3b6a50', '#244a36'],
}

/** Diverging polarity for "asking vs comparables": below (good for a buyer) ↔ above. */
export const DIVERGING: Record<Mode, { below: string; neutral: string; above: string }> = {
  dark: { below: '#a9cdb2', neutral: '#7d8a83', above: '#f08a7e' },
  light: { below: '#35604a', neutral: '#66726c', above: '#b3372d' },
}

/** Map surface the ramps were validated against (also the no-basemap background). */
export const SURFACE: Record<Mode, string> = { dark: '#090c0b', light: '#e9eeeb' }

/** Outline that separates dots from the ground, and the hover ring. */
export const STROKE: Record<Mode, string> = { dark: '#090c0b', light: '#ffffff' }
export const HOVER: Record<Mode, string> = { dark: '#eaefec', light: '#0f1412' }

/** Subject vs comparables (categorical: blue vs the sage accent, validated all-pairs). */
export const MARKERS: Record<Mode, { subject: string; comp: string }> = {
  dark: { subject: '#6ea8f0', comp: '#a9cdb2' },
  light: { subject: '#2a78d6', comp: '#35604a' },
}
