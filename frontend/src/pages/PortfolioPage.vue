<template>
  <div class="min-h-screen bg-slate-950 pt-16">
    <div class="max-w-screen-xl mx-auto px-4 py-8">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
          <h1 class="text-2xl font-bold text-white">My Portfolio</h1>
          <p class="text-slate-400 text-sm mt-1">{{ portfolioStore.savedHouses.length }} saved properties</p>
        </div>
        <router-link
          to="/search"
          class="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-xl transition-colors"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Add Properties
        </router-link>
      </div>

      <!-- Stats cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
          <p class="text-xs text-slate-400 mb-1">Total Properties</p>
          <p class="text-2xl font-bold text-white">{{ portfolioStore.savedHouses.length }}</p>
        </div>
        <div class="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
          <p class="text-xs text-slate-400 mb-1">Avg. Price</p>
          <p class="text-2xl font-bold text-violet-300">{{ avgPrice }}</p>
        </div>
        <div class="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
          <p class="text-xs text-slate-400 mb-1">Total Value</p>
          <p class="text-2xl font-bold text-emerald-300">{{ totalValue }}</p>
        </div>
        <div class="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
          <p class="text-xs text-slate-400 mb-1">Cities</p>
          <p class="text-2xl font-bold text-cyan-300">{{ uniqueCities }}</p>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="portfolioStore.loading" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <div v-for="i in 4" :key="i" class="bg-slate-800 rounded-xl h-48 animate-pulse"></div>
      </div>

      <!-- Empty state -->
      <div v-else-if="portfolioStore.savedHouses.length === 0" class="text-center py-16">
        <div class="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </div>
        <h3 class="text-white font-semibold mb-2">No saved properties yet</h3>
        <p class="text-slate-400 text-sm mb-6">Start browsing and save properties to track them here</p>
        <router-link
          to="/search"
          class="px-6 py-2.5 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-xl transition-colors"
        >
          Browse Properties
        </router-link>
      </div>

      <!-- Properties grid -->
      <div v-else>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <div
            v-for="entry in portfolioStore.savedHouses"
            :key="entry.id"
            class="relative group"
          >
            <HouseCard
              :house="entry.house"
              :is-saved="true"
              :show-save="true"
              @select="openDetail"
              @save="handleRemove(entry.house)"
            />
            <!-- Saved date badge -->
            <div class="absolute top-2 left-2 px-2 py-0.5 bg-violet-600/80 backdrop-blur-sm text-white text-xs rounded-full">
              Saved {{ formatDate(entry.saved_at) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail modal -->
    <HouseDetailModal
      v-if="selectedHouse"
      :house="selectedHouse"
      :is-saved="true"
      :show-save="true"
      @close="selectedHouse = null"
      @save="handleRemove(selectedHouse!)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePortfolioStore } from '@/stores/portfolio'
import HouseCard from '@/components/HouseCard.vue'
import HouseDetailModal from '@/components/HouseDetailModal.vue'
import type { House } from '@/types'

const portfolioStore = usePortfolioStore()
const selectedHouse = ref<House | null>(null)

const avgPrice = computed(() => {
  if (portfolioStore.savedHouses.length === 0) return '$0'
  const avg = portfolioStore.savedHouses.reduce((sum, e) => sum + e.house.price, 0) / portfolioStore.savedHouses.length
  if (avg >= 1_000_000) return `$${(avg / 1_000_000).toFixed(1)}M`
  if (avg >= 1_000) return `$${(avg / 1_000).toFixed(0)}K`
  return `$${avg}`
})

const totalValue = computed(() => {
  const total = portfolioStore.savedHouses.reduce((sum, e) => sum + e.house.price, 0)
  if (total >= 1_000_000) return `$${(total / 1_000_000).toFixed(1)}M`
  if (total >= 1_000) return `$${(total / 1_000).toFixed(0)}K`
  return `$${total}`
})

const uniqueCities = computed(() => {
  return new Set(portfolioStore.savedHouses.map((e) => e.house.city)).size
})

function openDetail(house: House) {
  selectedHouse.value = house
}

async function handleRemove(house: House) {
  await portfolioStore.removeHouse(house.id)
  if (selectedHouse.value?.id === house.id) selectedHouse.value = null
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' })
}

onMounted(() => portfolioStore.fetchSaved())
</script>
