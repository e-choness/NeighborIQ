<template>
  <div class="flex flex-col h-screen bg-slate-950 pt-16">
    <!-- Stats bar -->
    <div class="flex-shrink-0 bg-slate-900/80 border-b border-slate-700/50 px-4 py-2">
      <div class="flex items-center gap-6 text-xs">
        <span class="text-slate-400">
          <span class="text-white font-semibold">{{ housesStore.total.toLocaleString() }}</span>
          listings
        </span>
        <span class="text-slate-400">
          <span class="text-white font-semibold">{{ housesStore.filters.city || 'All cities' }}</span>
        </span>
        <span v-if="housesStore.loading" class="flex items-center gap-1 text-violet-400">
          <div class="animate-spin w-3 h-3 border border-violet-400 border-t-transparent rounded-full"></div>
          Loading...
        </span>
        <div class="ml-auto flex items-center gap-2">
          <button
            @click="viewMode = 'split'"
            class="view-btn" :class="{ 'view-btn-active': viewMode === 'split' }"
            title="Split view"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </button>
          <button
            @click="viewMode = 'map'"
            class="view-btn" :class="{ 'view-btn-active': viewMode === 'map' }"
            title="Map only"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          </button>
          <button
            @click="viewMode = 'list'"
            class="view-btn" :class="{ 'view-btn-active': viewMode === 'list' }"
            title="List only"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Main layout: filter | map/list -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Filter sidebar -->
      <FilterPanel
        v-model="housesStore.filters"
        class="hidden md:flex"
        @update:modelValue="onFilterUpdate"
      />

      <!-- Content area -->
      <div class="flex flex-1 overflow-hidden">
        <!-- Map panel -->
        <div
          v-if="viewMode !== 'list'"
          class="flex-1 overflow-hidden"
          :class="viewMode === 'split' ? 'w-1/2' : 'w-full'"
        >
          <MapView
            :houses="housesStore.houses"
            :selected-house="selectedHouse"
            :loading="housesStore.loading"
            @select-house="openDetail"
          />
        </div>

        <!-- List panel -->
        <div
          v-if="viewMode !== 'map'"
          class="overflow-y-auto bg-slate-900/50"
          :class="viewMode === 'split' ? 'w-1/2 border-l border-slate-700/50' : 'w-full'"
        >
          <!-- Error -->
          <div v-if="housesStore.error" class="m-4 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p class="text-sm text-red-300">{{ housesStore.error }}</p>
          </div>

          <!-- Loading skeleton -->
          <div v-if="housesStore.loading && housesStore.houses.length === 0" class="p-3 grid grid-cols-2 gap-3">
            <div v-for="i in 6" :key="i" class="bg-slate-800 rounded-xl h-48 animate-pulse"></div>
          </div>

          <!-- Empty state -->
          <div v-else-if="!housesStore.loading && housesStore.houses.length === 0" class="flex flex-col items-center justify-center h-full p-8 text-center">
            <svg class="w-12 h-12 text-slate-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <p class="text-slate-400 text-sm font-medium mb-1">No properties found</p>
            <p class="text-slate-600 text-xs">Try adjusting your filters or broadening the search area</p>
            <button
              @click="housesStore.resetFilters(); housesStore.fetchHouses()"
              class="mt-4 px-4 py-2 text-xs bg-violet-600/20 text-violet-400 border border-violet-500/30 rounded-lg hover:bg-violet-600/30 transition-colors"
            >
              Reset filters
            </button>
          </div>

          <!-- House grid -->
          <div v-else class="p-3 grid grid-cols-2 gap-3">
            <HouseCard
              v-for="house in housesStore.houses"
              :key="house.id"
              :house="house"
              :is-saved="portfolioStore.isSaved(house.id)"
              :show-save="authStore.isAuthenticated"
              @select="openDetail"
              @save="handleSave"
            />
          </div>

          <!-- Pagination -->
          <div
            v-if="housesStore.total > housesStore.filters.page_size"
            class="flex items-center justify-center gap-3 p-4 border-t border-slate-700/50"
          >
            <button
              @click="changePage(-1)"
              :disabled="housesStore.filters.page === 1"
              class="px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-30 text-white rounded-lg transition-colors"
            >
              Previous
            </button>
            <span class="text-xs text-slate-400">
              Page {{ housesStore.filters.page }} of {{ totalPages }}
            </span>
            <button
              @click="changePage(1)"
              :disabled="housesStore.filters.page >= totalPages"
              class="px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-30 text-white rounded-lg transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail modal -->
    <HouseDetailModal
      v-if="selectedHouse"
      :house="selectedHouse"
      :is-saved="portfolioStore.isSaved(selectedHouse.id)"
      :show-save="authStore.isAuthenticated"
      @close="selectedHouse = null"
      @save="handleSave(selectedHouse!)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useHousesStore } from '@/stores/houses'
import { useAuthStore } from '@/stores/auth'
import { usePortfolioStore } from '@/stores/portfolio'
import FilterPanel from '@/components/FilterPanel.vue'
import MapView from '@/components/MapView.vue'
import HouseCard from '@/components/HouseCard.vue'
import HouseDetailModal from '@/components/HouseDetailModal.vue'
import type { House, HouseFilters } from '@/types'

const housesStore = useHousesStore()
const authStore = useAuthStore()
const portfolioStore = usePortfolioStore()

const selectedHouse = ref<House | null>(null)
const viewMode = ref<'split' | 'map' | 'list'>('split')

const totalPages = computed(() =>
  Math.ceil(housesStore.total / housesStore.filters.page_size)
)

function onFilterUpdate(filters: Partial<HouseFilters>) {
  housesStore.updateFilters(filters)
  housesStore.fetchHouses()
}

function openDetail(house: House) {
  selectedHouse.value = house
}

async function handleSave(house: House) {
  if (!authStore.isAuthenticated) {
    // redirect to login
    return
  }
  try {
    if (portfolioStore.isSaved(house.id)) {
      await portfolioStore.removeHouse(house.id)
    } else {
      await portfolioStore.saveHouse(house.id)
    }
  } catch {
    // portfolio service may not exist yet
  }
}

function changePage(delta: number) {
  const newPage = housesStore.filters.page + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    housesStore.setPage(newPage)
    housesStore.fetchHouses()
  }
}

onMounted(async () => {
  await housesStore.fetchHouses()
  if (authStore.isAuthenticated) {
    await portfolioStore.fetchSaved().catch(() => {})
  }
})
</script>

<style scoped>
.view-btn {
  @apply p-1.5 rounded-md text-slate-500 hover:text-slate-200 hover:bg-slate-700/50 transition-all;
}
.view-btn-active {
  @apply text-violet-400 bg-violet-500/10;
}
</style>
