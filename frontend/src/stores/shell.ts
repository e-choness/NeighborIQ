/**
 * App-shell state shared by the sheets, the map and the pages: the phone sheet snap,
 * a transient toast, and the last Explore query (so a listing's back/close button
 * returns to the same filters).
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { LocationQuery } from 'vue-router'
import { viewport } from '@/lib/viewport'

export type Snap = 'peek' | 'half' | 'full'
export const SNAPS: Snap[] = ['peek', 'half', 'full']

export const useShell = defineStore('shell', () => {
  const snap = ref<Snap>('half')
  /** Phone sheet height in px for the current snap (the map pads its bottom by this + 10). */
  const sheetHeight = computed(() => {
    const vh = viewport.height
    if (snap.value === 'peek') return Math.round(Math.min(250, vh * 0.4))
    if (snap.value === 'half') return Math.round(vh * 0.56)
    return vh - 108
  })
  function step(delta: 1 | -1) {
    const i = SNAPS.indexOf(snap.value)
    snap.value = SNAPS[Math.max(0, Math.min(SNAPS.length - 1, i + delta))]
  }
  function cycle() {
    snap.value = SNAPS[(SNAPS.indexOf(snap.value) + 1) % SNAPS.length]
  }

  const toast = ref('')
  let toastTimer: ReturnType<typeof setTimeout> | undefined
  function flash(message: string) {
    clearTimeout(toastTimer)
    toast.value = message
    toastTimer = setTimeout(() => (toast.value = ''), 2200)
  }

  const exploreQuery = ref<LocationQuery>({})

  return { snap, sheetHeight, step, cycle, toast, flash, exploreQuery }
})
