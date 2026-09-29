/**
 * The city every map screen shows. Lives in the top bar and is mirrored in `?city=`,
 * so links stay shareable; falls back to the first market with listings.
 */
import { useQuery } from '@pinia/colada'
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { api } from '@/lib/api'
import type { Market } from '@/lib/types'
import router from '@/router'

export const useCity = defineStore('city', () => {
  const { data: markets, isLoading } = useQuery({ key: ['markets'], query: () => api<Market[]>('/markets') })
  const city = ref('')

  watch(
    () => router.currentRoute.value.query.city,
    (q) => {
      if (typeof q === 'string' && q) city.value = q
    },
    { immediate: true },
  )
  watch(
    [markets, city],
    ([m]) => {
      if (m?.length && !m.some((x) => x.city === city.value)) city.value = m[0].city
    },
    { immediate: true },
  )

  const market = computed(() => markets.value?.find((m) => m.city === city.value) ?? null)

  /** Switch city from the top bar. A listing belongs to one city, so leave it for Explore. */
  function select(next: string) {
    if (next === city.value) return
    city.value = next
    const route = router.currentRoute.value
    if (route.name === 'listing') router.push({ path: '/explore', query: { city: next } })
    else router.replace({ query: { ...route.query, city: next, bbox: undefined } })
  }

  return { city, markets, market, isLoading, select }
})
