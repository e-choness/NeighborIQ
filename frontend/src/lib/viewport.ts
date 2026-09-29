/**
 * Shared viewport state for the map-first shell. Breakpoints (see docs/development/frontend.md):
 * phone layout below 1024px, Home stat tiles from 1100px, the floating best-yields row from 1280px.
 */
import { computed, reactive } from 'vue'

export const viewport = reactive({ width: window.innerWidth, height: window.innerHeight })

window.addEventListener(
  'resize',
  () => Object.assign(viewport, { width: window.innerWidth, height: window.innerHeight }),
  { passive: true },
)

export const isPhone = computed(() => viewport.width < 1024)
export const showStatTiles = computed(() => viewport.width >= 1100)
export const showBestRow = computed(() => viewport.width >= 1280)
