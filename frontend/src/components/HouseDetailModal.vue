<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-[100] flex items-center justify-center p-4"
      @click.self="$emit('close')"
    >
      <!-- Backdrop -->
      <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="$emit('close')"></div>

      <!-- Modal -->
      <div class="relative w-full max-w-2xl max-h-[90vh] bg-slate-800 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl animate-slide-up z-10">
        <!-- Header image -->
        <div class="relative h-48 bg-slate-700 overflow-hidden">
          <img
            v-if="house.images && house.images.length > 0"
            :src="house.images[0]"
            :alt="house.title"
            class="w-full h-full object-cover"
          />
          <div v-else class="w-full h-full flex items-center justify-center">
            <svg class="w-16 h-16 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
          </div>

          <!-- Gradient overlay -->
          <div class="absolute inset-0 bg-gradient-to-t from-slate-800 via-transparent to-transparent"></div>

          <!-- Close button -->
          <button
            @click="$emit('close')"
            class="absolute top-3 right-3 w-8 h-8 bg-slate-900/80 backdrop-blur rounded-full flex items-center justify-center text-white hover:bg-slate-700 transition-colors"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>

          <!-- Price badge -->
          <div class="absolute bottom-3 left-4">
            <p class="text-2xl font-bold text-white">{{ formatPrice(house.price) }}</p>
            <p class="text-xs text-slate-300">{{ house.area }} m² · CAD</p>
          </div>
        </div>

        <!-- Scrollable content -->
        <div class="overflow-y-auto max-h-[calc(90vh-192px)]">
          <div class="p-5">
            <!-- Title and location -->
            <h2 class="text-lg font-semibold text-white mb-1">{{ house.title }}</h2>
            <p class="text-sm text-slate-400 flex items-center gap-1.5 mb-4">
              <svg class="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {{ house.community }}, {{ house.region }}, {{ house.city }}
            </p>

            <!-- Property details grid -->
            <div class="grid grid-cols-3 gap-3 mb-5">
              <div class="bg-slate-700/40 rounded-lg p-3 text-center">
                <p class="text-xl font-bold text-white">{{ house.rooms }}</p>
                <p class="text-xs text-slate-400">Bedrooms</p>
              </div>
              <div class="bg-slate-700/40 rounded-lg p-3 text-center">
                <p class="text-xl font-bold text-white">{{ house.area }}</p>
                <p class="text-xs text-slate-400">m²</p>
              </div>
              <div class="bg-slate-700/40 rounded-lg p-3 text-center">
                <p class="text-xl font-bold text-white">{{ house.floor ?? '—' }}</p>
                <p class="text-xs text-slate-400">Floor</p>
              </div>
            </div>

            <!-- Additional info -->
            <div class="flex flex-wrap gap-2 mb-5">
              <span v-if="house.decoration" class="detail-chip">{{ house.decoration }}</span>
              <span v-if="house.age" class="detail-chip">{{ house.age }} years old</span>
              <span class="detail-chip">{{ house.street }}</span>
            </div>

            <!-- AI Insights section -->
            <div class="border-t border-slate-700/50 pt-4">
              <div v-if="insightsLoading" class="flex items-center gap-2 py-3">
                <div class="animate-spin w-4 h-4 border-2 border-violet-500 border-t-transparent rounded-full"></div>
                <span class="text-xs text-slate-400">Loading AI insights...</span>
              </div>
              <InsightsDashboard v-else :insights="insights" />
            </div>

            <!-- Action buttons -->
            <div class="flex gap-3 mt-5">
              <button
                v-if="showSave"
                @click="$emit('save')"
                class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-medium text-sm transition-all"
                :class="isSaved
                  ? 'bg-violet-600/30 border border-violet-500/50 text-violet-300'
                  : 'bg-violet-600 hover:bg-violet-500 text-white'"
              >
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path v-if="isSaved" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  <path v-else fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                {{ isSaved ? 'Saved' : 'Save to Portfolio' }}
              </button>
              <a
                v-if="house.url"
                :href="house.url"
                target="_blank"
                rel="noopener noreferrer"
                class="flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium rounded-xl transition-colors"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                View listing
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import InsightsDashboard from './InsightsDashboard.vue'
import { insightsApi } from '@/services/api'
import type { House, HouseInsights } from '@/types'

const props = defineProps<{
  house: House
  isSaved?: boolean
  showSave?: boolean
}>()

defineEmits<{
  close: []
  save: []
}>()

const insights = ref<HouseInsights | null>(null)
const insightsLoading = ref(false)

async function loadInsights() {
  insightsLoading.value = true
  try {
    const response = await insightsApi.houseInsights(props.house.id)
    insights.value = response.data
  } catch {
    insights.value = null
  } finally {
    insightsLoading.value = false
  }
}

watch(() => props.house.id, loadInsights, { immediate: true })

function formatPrice(price: number): string {
  if (price >= 1_000_000) return `$${(price / 1_000_000).toFixed(2)}M`
  if (price >= 1_000) return `$${(price / 1_000).toFixed(0)}K`
  return `$${price}`
}
</script>

<style scoped>
.detail-chip {
  @apply inline-block px-2.5 py-1 bg-slate-700/60 text-slate-300 text-xs rounded-full border border-slate-600/40;
}
</style>
