<template>
  <aside class="w-64 flex-shrink-0 bg-slate-800/60 border-r border-slate-700/50 overflow-y-auto">
    <div class="p-4">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-semibold text-white">Filters</h2>
        <button
          @click="resetFilters"
          class="text-xs text-slate-400 hover:text-violet-400 transition-colors"
        >
          Reset all
        </button>
      </div>

      <!-- City -->
      <div class="mb-4">
        <label class="filter-label">City</label>
        <input
          v-model="localFilters.city"
          type="text"
          placeholder="e.g. Toronto"
          class="filter-input"
          @change="emitFilters"
        />
      </div>

      <!-- Region -->
      <div class="mb-4">
        <label class="filter-label">Region / Neighborhood</label>
        <input
          v-model="localFilters.region"
          type="text"
          placeholder="e.g. Downtown"
          class="filter-input"
          @change="emitFilters"
        />
      </div>

      <!-- Price range -->
      <div class="mb-4">
        <label class="filter-label">Price Range (CAD)</label>
        <div class="flex gap-2">
          <input
            v-model.number="localFilters.price_min"
            type="number"
            placeholder="Min"
            min="0"
            class="filter-input"
            @change="emitFilters"
          />
          <input
            v-model.number="localFilters.price_max"
            type="number"
            placeholder="Max"
            min="0"
            class="filter-input"
            @change="emitFilters"
          />
        </div>
        <!-- Quick presets -->
        <div class="flex flex-wrap gap-1 mt-2">
          <button
            v-for="preset in pricePresets"
            :key="preset.label"
            @click="applyPricePreset(preset)"
            class="text-xs px-2 py-1 rounded-md bg-slate-700/60 text-slate-400 hover:bg-violet-600/20 hover:text-violet-300 transition-colors"
          >
            {{ preset.label }}
          </button>
        </div>
      </div>

      <!-- Bedrooms -->
      <div class="mb-4">
        <label class="filter-label">Bedrooms</label>
        <div class="flex gap-1.5 flex-wrap">
          <button
            v-for="n in [1, 2, 3, 4, 5]"
            :key="n"
            @click="toggleRoom(n)"
            class="w-9 h-9 rounded-lg text-sm font-medium transition-all"
            :class="isRoomSelected(n)
              ? 'bg-violet-600 text-white border border-violet-500'
              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 border border-slate-600/50'"
          >
            {{ n }}{{ n === 5 ? '+' : '' }}
          </button>
        </div>
      </div>

      <!-- Area -->
      <div class="mb-4">
        <label class="filter-label">Area (m²)</label>
        <div class="flex gap-2">
          <input
            v-model.number="localFilters.area_min"
            type="number"
            placeholder="Min"
            min="0"
            class="filter-input"
            @change="emitFilters"
          />
          <input
            v-model.number="localFilters.area_max"
            type="number"
            placeholder="Max"
            min="0"
            class="filter-input"
            @change="emitFilters"
          />
        </div>
      </div>

      <!-- Sort -->
      <div class="mb-4">
        <label class="filter-label">Sort by</label>
        <select
          v-model="localFilters.sort"
          class="filter-input"
          @change="emitFilters"
        >
          <option value="created_at">Newest first</option>
          <option value="price">Price</option>
          <option value="area">Area</option>
        </select>
        <div class="flex gap-2 mt-2">
          <button
            @click="localFilters.order = 'desc'; emitFilters()"
            class="flex-1 text-xs py-1.5 rounded-lg transition-colors"
            :class="localFilters.order === 'desc'
              ? 'bg-violet-600/30 text-violet-300 border border-violet-500/30'
              : 'bg-slate-700/40 text-slate-400 border border-slate-600/30'"
          >
            High → Low
          </button>
          <button
            @click="localFilters.order = 'asc'; emitFilters()"
            class="flex-1 text-xs py-1.5 rounded-lg transition-colors"
            :class="localFilters.order === 'asc'
              ? 'bg-violet-600/30 text-violet-300 border border-violet-500/30'
              : 'bg-slate-700/40 text-slate-400 border border-slate-600/30'"
          >
            Low → High
          </button>
        </div>
      </div>

      <!-- Apply button -->
      <button
        @click="emitFilters"
        class="w-full py-2.5 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors"
      >
        Apply Filters
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { HouseFilters } from '@/types'

const props = defineProps<{
  modelValue: HouseFilters
}>()

const emit = defineEmits<{
  'update:modelValue': [filters: Partial<HouseFilters>]
}>()

const localFilters = reactive({
  city: props.modelValue.city,
  region: props.modelValue.region,
  price_min: props.modelValue.price_min,
  price_max: props.modelValue.price_max,
  rooms_min: props.modelValue.rooms_min,
  rooms_max: props.modelValue.rooms_max,
  area_min: props.modelValue.area_min,
  area_max: props.modelValue.area_max,
  sort: props.modelValue.sort,
  order: props.modelValue.order,
})

// Sync localFilters when parent resets store filters externally (BUG-6-006)
watch(() => props.modelValue, (v) => Object.assign(localFilters, v), { deep: true })

const pricePresets = [
  { label: 'Under $500K', min: null, max: 500000 },
  { label: '$500K–$1M', min: 500000, max: 1000000 },
  { label: '$1M–$2M', min: 1000000, max: 2000000 },
  { label: '$2M+', min: 2000000, max: null },
]

function applyPricePreset(preset: { min: number | null; max: number | null }) {
  localFilters.price_min = preset.min
  localFilters.price_max = preset.max
  emitFilters()
}

function isRoomSelected(n: number): boolean {
  if (n === 5) return localFilters.rooms_min === 5
  return localFilters.rooms_min === n && localFilters.rooms_max === n
}

function toggleRoom(n: number) {
  if (isRoomSelected(n)) {
    localFilters.rooms_min = null
    localFilters.rooms_max = null
  } else if (n === 5) {
    localFilters.rooms_min = 5
    localFilters.rooms_max = null
  } else {
    localFilters.rooms_min = n
    localFilters.rooms_max = n
  }
  emitFilters()
}

function emitFilters() {
  emit('update:modelValue', { ...localFilters })
}

function resetFilters() {
  Object.assign(localFilters, {
    city: '',
    region: '',
    price_min: null,
    price_max: null,
    rooms_min: null,
    rooms_max: null,
    area_min: null,
    area_max: null,
    sort: 'created_at',
    order: 'desc',
  })
  emitFilters()
}
</script>

<style scoped>
.filter-label {
  @apply block text-xs font-medium text-slate-400 mb-1.5;
}
.filter-input {
  @apply w-full bg-slate-700/50 border border-slate-600/50 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-violet-500/50 focus:border-violet-500/50 transition-colors;
}
</style>
