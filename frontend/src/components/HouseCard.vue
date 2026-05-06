<template>
  <div
    class="group bg-slate-800 border border-slate-700/50 rounded-xl overflow-hidden hover:border-violet-500/50 hover:shadow-lg hover:shadow-violet-500/5 transition-all duration-200 cursor-pointer"
    @click="$emit('select', house)"
  >
    <!-- Image / placeholder -->
    <div class="relative h-36 bg-slate-700/50 overflow-hidden">
      <img
        v-if="house.images && house.images.length > 0"
        :src="house.images[0]"
        :alt="house.title"
        class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        loading="lazy"
      />
      <div v-else class="w-full h-full flex items-center justify-center">
        <svg class="w-12 h-12 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
            d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      </div>
      <!-- Price badge -->
      <div class="absolute bottom-2 left-2 px-2 py-1 bg-slate-900/90 backdrop-blur-sm rounded-lg">
        <span class="text-white font-bold text-sm">{{ formatPrice(house.price) }}</span>
      </div>
      <!-- Save button -->
      <button
        v-if="showSave"
        @click.stop="$emit('save', house)"
        class="absolute top-2 right-2 w-8 h-8 flex items-center justify-center rounded-full backdrop-blur-sm transition-all"
        :class="isSaved
          ? 'bg-violet-500 text-white'
          : 'bg-slate-900/80 text-slate-400 hover:text-violet-400'"
        :title="isSaved ? 'Remove from portfolio' : 'Save to portfolio'"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
          <path v-if="isSaved" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          <path v-else fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
        </svg>
      </button>
    </div>

    <!-- Card body -->
    <div class="p-3">
      <h3 class="text-sm font-medium text-white truncate mb-1 group-hover:text-violet-300 transition-colors">
        {{ house.title }}
      </h3>
      <p class="text-xs text-slate-400 truncate mb-2">
        {{ house.community }}, {{ house.region }}, {{ house.city }}
      </p>

      <!-- Stats row -->
      <div class="flex items-center gap-3 text-xs text-slate-400">
        <span class="flex items-center gap-1">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
          {{ house.area }} m²
        </span>
        <span class="flex items-center gap-1">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          {{ house.rooms }} bed
        </span>
        <span v-if="house.floor" class="flex items-center gap-1">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
          Fl. {{ house.floor }}
        </span>
        <span v-if="house.age" class="ml-auto text-slate-500">{{ house.age }}yr</span>
      </div>

      <!-- Decoration badge -->
      <div v-if="house.decoration" class="mt-2">
        <span class="inline-block px-2 py-0.5 bg-slate-700/60 text-slate-300 text-xs rounded-full">
          {{ house.decoration }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { House } from '@/types'

const props = defineProps<{
  house: House
  isSaved?: boolean
  showSave?: boolean
}>()

defineEmits<{
  select: [house: House]
  save: [house: House]
}>()

function formatPrice(price: number): string {
  if (price >= 1_000_000) return `$${(price / 1_000_000).toFixed(1)}M`
  if (price >= 1_000) return `$${(price / 1_000).toFixed(0)}K`
  return `$${price}`
}
</script>
