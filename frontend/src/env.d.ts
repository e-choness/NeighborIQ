/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Self-hosted Protomaps basemap, e.g. /tiles/canada.pmtiles (map renders without a basemap when unset) */
  readonly VITE_PMTILES_URL?: string
  readonly VITE_MAP_GLYPHS?: string
  readonly VITE_MAP_SPRITE?: string
}
