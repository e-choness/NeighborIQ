/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Basemap source: a hosted vector style (default), the self-hosted PMTiles file, or none (data only) */
  readonly VITE_BASEMAP?: 'hosted' | 'pmtiles' | 'none'
  /** Hosted style URLs (default: OpenFreeMap dark / positron) */
  readonly VITE_BASEMAP_STYLE_DARK?: string
  readonly VITE_BASEMAP_STYLE_LIGHT?: string
  /** Self-hosted Protomaps basemap, e.g. /tiles/canada.pmtiles (takes precedence over VITE_BASEMAP) */
  readonly VITE_PMTILES_URL?: string
  readonly VITE_MAP_GLYPHS?: string
  readonly VITE_MAP_SPRITE?: string
  /** Set by the Playwright build: exposes the map on window.__hexmap */
  readonly VITE_E2E?: string
}
