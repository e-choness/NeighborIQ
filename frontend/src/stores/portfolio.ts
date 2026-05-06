import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import type { House } from '@/types'

export interface SavedHouseEntry {
  id: number
  house_id: number
  house: House
  saved_at: string
  notes: string | null
}

export const usePortfolioStore = defineStore('portfolio', () => {
  const savedHouses = ref<SavedHouseEntry[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const savedIds = ref<Set<number>>(new Set())

  async function fetchSaved() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get<SavedHouseEntry[]>('/portfolio/saved')
      savedHouses.value = response.data
      savedIds.value = new Set(response.data.map((e) => e.house_id))
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      error.value = e.response?.data?.detail ?? 'Failed to fetch portfolio'
    } finally {
      loading.value = false
    }
  }

  async function saveHouse(houseId: number) {
    try {
      await api.post('/portfolio/save', { house_id: houseId })
      savedIds.value.add(houseId)
      await fetchSaved()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      error.value = e.response?.data?.detail ?? 'Failed to save house'
      throw err
    }
  }

  async function removeHouse(houseId: number) {
    try {
      await api.delete(`/portfolio/saved/${houseId}`)
      savedIds.value.delete(houseId)
      savedHouses.value = savedHouses.value.filter((e) => e.house_id !== houseId)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      error.value = e.response?.data?.detail ?? 'Failed to remove house'
      throw err
    }
  }

  function isSaved(houseId: number) {
    return savedIds.value.has(houseId)
  }

  return {
    savedHouses,
    loading,
    error,
    savedIds,
    fetchSaved,
    saveHouse,
    removeHouse,
    isSaved,
  }
})
