import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { housesApi } from '@/services/api'
import type { House, HouseFilters, Community } from '@/types'

const DEFAULT_FILTERS: HouseFilters = {
  city: '',
  region: '',
  price_min: null,
  price_max: null,
  rooms_min: null,
  rooms_max: null,
  area_min: null,
  area_max: null,
  page: 1,
  page_size: 50,
  sort: 'created_at',
  order: 'desc',
}

export const useHousesStore = defineStore('houses', () => {
  const houses = ref<House[]>([])
  const communities = ref<Community[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const filters = reactive<HouseFilters>({ ...DEFAULT_FILTERS })

  async function fetchHouses() {
    loading.value = true
    error.value = null
    try {
      const params: Record<string, unknown> = {}
      if (filters.city) params.city = filters.city
      if (filters.region) params.region = filters.region
      if (filters.price_min !== null) params.price_min = filters.price_min
      if (filters.price_max !== null) params.price_max = filters.price_max
      if (filters.rooms_min !== null) params.rooms_min = filters.rooms_min
      if (filters.rooms_max !== null) params.rooms_max = filters.rooms_max
      if (filters.area_min !== null) params.area_min = filters.area_min
      if (filters.area_max !== null) params.area_max = filters.area_max
      params.page = filters.page
      params.page_size = filters.page_size
      params.sort = filters.sort
      params.order = filters.order

      const response = await housesApi.list(params as Partial<HouseFilters>)
      houses.value = response.data.items
      total.value = response.data.total
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      error.value = e.response?.data?.detail ?? 'Failed to fetch houses'
    } finally {
      loading.value = false
    }
  }

  async function fetchCommunities(city?: string, region?: string) {
    try {
      const response = await housesApi.communities(city, region)
      communities.value = response.data.items
    } catch {
      communities.value = []
    }
  }

  function updateFilters(newFilters: Partial<HouseFilters>) {
    Object.assign(filters, newFilters)
    filters.page = 1
  }

  function resetFilters() {
    Object.assign(filters, DEFAULT_FILTERS)
  }

  function setPage(page: number) {
    filters.page = page
  }

  return {
    houses,
    communities,
    total,
    loading,
    error,
    filters,
    fetchHouses,
    fetchCommunities,
    updateFilters,
    resetFilters,
    setPage,
  }
})
