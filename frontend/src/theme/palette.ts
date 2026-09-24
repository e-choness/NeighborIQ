/**
 * Map and data colours — the single place to change them.
 *
 * The basemap (Protomaps flavor) and every data layer read from here. To adopt
 * another visual identity (e.g. GISCARTA's map contrast), replace the hex values
 * below; the data ramps were validated for step visibility, colour-vision
 * deficiency separation and contrast against the map surface — re-run the
 * validator (docs/frontend/overview.md) after changing them.
 */
import { namedFlavor, type Flavor } from '@protomaps/basemaps'

export type Mode = 'dark' | 'light'

/** Basemap: low-contrast ground so data layers carry the contrast. */
export const BASEMAP: Record<Mode, Partial<Flavor>> = {
  dark: {
    background: '#0b0f14',
    earth: '#0e141b',
    water: '#06080c',
    park_a: '#0f1a19', park_b: '#0f1a19', wood_a: '#0f1a19', wood_b: '#0f1a19',
    buildings: '#141c26',
    minor_a: '#18212c', minor_b: '#18212c', minor_service: '#151d27', other: '#151d27',
    link: '#1d2835', major: '#223040', highway: '#2a3a4e', railway: '#1d2835',
    boundaries: '#2f3d4f',
    roads_label_minor: '#58677a', roads_label_major: '#6f7f92',
    roads_label_minor_halo: '#0b0f14', roads_label_major_halo: '#0b0f14',
    subplace_label: '#7d8ca0', subplace_label_halo: '#0b0f14',
    city_label: '#a7b3c2', city_label_halo: '#0b0f14',
  },
  light: {
    background: '#f2f4f6',
    earth: '#eef1f4',
    water: '#d6e0e8',
    park_a: '#e4ece6', park_b: '#e4ece6', wood_a: '#e4ece6', wood_b: '#e4ece6',
    buildings: '#e2e6eb',
    minor_a: '#ffffff', minor_b: '#ffffff', major: '#ffffff', highway: '#f8f9fa',
  },
}

export function basemapFlavor(mode: Mode): Flavor {
  return { ...namedFlavor(mode === 'dark' ? 'dark' : 'light'), ...BASEMAP[mode] }
}

/** Sequential magnitude (one hue, teal): low → high. Validated as ordinal ramps. */
export const SEQUENTIAL: Record<Mode, string[]> = {
  dark: ['#115e59', '#0f766e', '#0d9488', '#14b8a6', '#2dd4bf', '#5eead4'],
  light: ['#14b8a6', '#0d9488', '#0f766e', '#115e59'],
}

/** Diverging polarity for "asking vs comparables": below (good for a buyer) ↔ above. */
export const DIVERGING: Record<Mode, { below: string; neutral: string; above: string }> = {
  dark: { below: '#0d9488', neutral: '#3a4452', above: '#e5484d' },
  light: { below: '#0d9488', neutral: '#c9cfd6', above: '#d03b3b' },
}

/** Map surface the ramps were validated against. */
export const SURFACE: Record<Mode, string> = { dark: '#0b0f14', light: '#ffffff' }

/** Subject vs comparables on small maps (categorical slots 1 and 3, validated all-pairs). */
export const MARKERS: Record<Mode, { subject: string; comp: string }> = {
  dark: { subject: '#3987e5', comp: '#199e70' },
  light: { subject: '#2a78d6', comp: '#1baf7a' },
}
