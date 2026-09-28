import { Bookmark, Calculator, Database, Map, Search } from '@lucide/vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

export const NAV = [
  { to: '/', name: 'home', label: 'Map', short: 'Map', icon: Map },
  { to: '/explore', name: 'explore', label: 'Explore', short: 'Explore', icon: Search },
  { to: '/analyze', name: 'analyze', label: 'Analyze', short: 'Analyze', icon: Calculator },
  { to: '/portfolio', name: 'portfolio', label: 'Portfolio', short: 'Saved', icon: Bookmark },
  { to: '/data', name: 'data', label: 'Sources & admin', short: 'Data', icon: Database },
] as const

/** The nav item for the current route (a listing belongs to Explore). */
export function useActiveNav() {
  const route = useRoute()
  return computed(() => {
    const name = route.name === 'listing' ? 'explore' : route.name
    return Math.max(0, NAV.findIndex((n) => n.name === name))
  })
}
