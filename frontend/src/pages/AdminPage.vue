<template>
  <div class="min-h-screen bg-slate-950 pt-16">
    <div class="max-w-screen-xl mx-auto px-4 py-8">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-2xl font-bold text-white">Admin Dashboard</h1>
        <p class="text-slate-400 text-sm mt-1">Manage listings, users, and monitor system health</p>
      </div>

      <!-- Tab nav -->
      <div class="flex gap-1 mb-6 border-b border-slate-700/50 pb-0">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          class="px-4 py-2.5 text-sm font-medium border-b-2 transition-all -mb-px"
          :class="activeTab === tab.id
            ? 'text-white border-violet-500'
            : 'text-slate-400 border-transparent hover:text-white'"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Houses tab -->
      <div v-if="activeTab === 'houses'">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-white">House Listings</h2>
          <div class="flex gap-2">
            <input
              v-model="houseSearch"
              type="text"
              placeholder="Search listings..."
              class="admin-input w-48"
              @input="fetchHouses"
            />
            <button
              @click="showAddHouse = true"
              class="px-3 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm rounded-lg transition-colors flex items-center gap-1.5"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              Add Listing
            </button>
          </div>
        </div>

        <!-- Houses table -->
        <div class="bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="border-b border-slate-700/50 bg-slate-800/60">
                  <th class="table-th text-left">ID</th>
                  <th class="table-th text-left">Title</th>
                  <th class="table-th text-left">City / Region</th>
                  <th class="table-th text-right">Price</th>
                  <th class="table-th text-center">Rooms</th>
                  <th class="table-th text-center">Area</th>
                  <th class="table-th text-center">Added</th>
                  <th class="table-th text-center">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-if="housesStore.loading"
                  class="border-b border-slate-700/30"
                >
                  <td colspan="8" class="py-8 text-center text-slate-500 text-sm">Loading...</td>
                </tr>
                <tr
                  v-else-if="housesStore.houses.length === 0"
                  class="border-b border-slate-700/30"
                >
                  <td colspan="8" class="py-8 text-center text-slate-500 text-sm">No listings found</td>
                </tr>
                <tr
                  v-for="house in housesStore.houses"
                  :key="house.id"
                  class="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors"
                >
                  <td class="table-td text-slate-500 font-mono text-xs">#{{ house.id }}</td>
                  <td class="table-td">
                    <div class="max-w-xs">
                      <p class="text-sm text-white truncate">{{ house.title }}</p>
                      <p class="text-xs text-slate-500 truncate">{{ house.community }}</p>
                    </div>
                  </td>
                  <td class="table-td">
                    <p class="text-sm text-slate-300">{{ house.city }}</p>
                    <p class="text-xs text-slate-500">{{ house.region }}</p>
                  </td>
                  <td class="table-td text-right">
                    <span class="text-sm font-semibold text-violet-300">{{ formatPrice(house.price) }}</span>
                  </td>
                  <td class="table-td text-center text-sm text-slate-300">{{ house.rooms }}</td>
                  <td class="table-td text-center text-sm text-slate-300">{{ house.area }}m²</td>
                  <td class="table-td text-center text-xs text-slate-500">{{ formatDate(house.created_at) }}</td>
                  <td class="table-td text-center">
                    <div class="flex items-center justify-center gap-1">
                      <button
                        @click="editHouse(house)"
                        class="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                        title="Edit"
                      >
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        @click="confirmDelete(house)"
                        class="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                        title="Delete"
                      >
                        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          <div class="flex items-center justify-between px-4 py-3 border-t border-slate-700/50">
            <span class="text-xs text-slate-500">
              {{ housesStore.total }} total listings
            </span>
            <div class="flex gap-2">
              <button
                @click="changePage(-1)"
                :disabled="housesStore.filters.page === 1"
                class="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-30 text-white rounded-lg transition-colors"
              >Prev</button>
              <span class="text-xs text-slate-400 px-2 flex items-center">
                {{ housesStore.filters.page }} / {{ totalPages }}
              </span>
              <button
                @click="changePage(1)"
                :disabled="housesStore.filters.page >= totalPages"
                class="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-30 text-white rounded-lg transition-colors"
              >Next</button>
            </div>
          </div>
        </div>
      </div>

      <!-- System Status tab -->
      <div v-if="activeTab === 'system'" class="space-y-4">
        <h2 class="text-base font-semibold text-white mb-4">Service Health</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="service in serviceHealth"
            :key="service.name"
            class="bg-slate-800/40 border rounded-xl p-4 flex items-center gap-3"
            :class="service.status === 'ok' ? 'border-emerald-500/20' : service.status === 'checking' ? 'border-slate-700/50' : 'border-red-500/20'"
          >
            <div
              class="w-2.5 h-2.5 rounded-full flex-shrink-0"
              :class="service.status === 'ok' ? 'bg-emerald-400 animate-pulse-slow' : service.status === 'checking' ? 'bg-slate-500 animate-pulse' : 'bg-red-400'"
            ></div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-white">{{ service.name }}</p>
              <p class="text-xs text-slate-400">port {{ service.port }}</p>
            </div>
            <span
              class="text-xs px-2 py-0.5 rounded-full"
              :class="service.status === 'ok'
                ? 'bg-emerald-500/20 text-emerald-400'
                : service.status === 'checking'
                ? 'bg-slate-600/50 text-slate-400'
                : 'bg-red-500/20 text-red-400'"
            >
              {{ service.status }}
            </span>
          </div>
        </div>

        <button
          @click="checkAllServices"
          class="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors flex items-center gap-2"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh status
        </button>
      </div>
    </div>

    <!-- Delete confirmation modal -->
    <div
      v-if="deleteTarget"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      @click.self="deleteTarget = null"
    >
      <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6 w-full max-w-sm shadow-xl">
        <h3 class="text-white font-semibold mb-2">Delete listing?</h3>
        <p class="text-slate-400 text-sm mb-5">
          This will soft-delete "<span class="text-white">{{ deleteTarget.title }}</span>". This action can be reversed from the database.
        </p>
        <div class="flex gap-3">
          <button
            @click="deleteTarget = null"
            class="flex-1 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-xl transition-colors"
          >Cancel</button>
          <button
            @click="executeDelete"
            class="flex-1 py-2 bg-red-600 hover:bg-red-500 text-white text-sm rounded-xl transition-colors"
          >Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useHousesStore } from '@/stores/houses'
import { housesApi } from '@/services/api'
import api from '@/services/api'
import type { House } from '@/types'

const housesStore = useHousesStore()

const activeTab = ref('houses')
const houseSearch = ref('')
const showAddHouse = ref(false)
const deleteTarget = ref<House | null>(null)

const tabs = [
  { id: 'houses', label: 'Listings' },
  { id: 'system', label: 'System Health' },
]

const serviceHealth = reactive([
  { name: 'API Gateway', port: 8000, status: 'checking' },
  { name: 'Auth Service', port: 8001, status: 'checking' },
  { name: 'House API', port: 8002, status: 'checking' },
  { name: 'AI Insights', port: 8003, status: 'checking' },
  { name: 'Search Service', port: 8004, status: 'checking' },
])

const totalPages = computed(() =>
  Math.ceil(housesStore.total / housesStore.filters.page_size)
)

function formatPrice(price: number): string {
  if (price >= 1_000_000) return `$${(price / 1_000_000).toFixed(1)}M`
  if (price >= 1_000) return `$${(price / 1_000).toFixed(0)}K`
  return `$${price}`
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: '2-digit' })
}

async function fetchHouses() {
  await housesStore.fetchHouses()
}

function editHouse(_house: House) {
  // TODO: implement edit modal
}

function confirmDelete(house: House) {
  deleteTarget.value = house
}

async function executeDelete() {
  if (!deleteTarget.value) return
  try {
    await housesApi.delete(deleteTarget.value.id)
    await housesStore.fetchHouses()
  } finally {
    deleteTarget.value = null
  }
}

function changePage(delta: number) {
  const newPage = housesStore.filters.page + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    housesStore.setPage(newPage)
    housesStore.fetchHouses()
  }
}

async function checkAllServices() {
  for (const service of serviceHealth) {
    service.status = 'checking'
  }

  const endpoints = [
    { idx: 0, path: '/health' },
    { idx: 1, path: '/api/v1/auth/health' },  // via gateway proxy
    { idx: 2, path: '/api/v1/houses/health' }, // via gateway proxy
    { idx: 3, path: '/api/v1/ai/health' },
    { idx: 4, path: '/api/v1/search/health' },
  ]

  for (const { idx, path } of endpoints) {
    try {
      await api.get(path, { timeout: 3000 })
      serviceHealth[idx].status = 'ok'
    } catch {
      serviceHealth[idx].status = 'error'
    }
  }
}

onMounted(async () => {
  await housesStore.fetchHouses()
  checkAllServices()
})
</script>

<style scoped>
.table-th {
  @apply px-4 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wider;
}
.table-td {
  @apply px-4 py-3;
}
.admin-input {
  @apply bg-slate-700/50 border border-slate-600/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-violet-500/50 transition-colors;
}
</style>
