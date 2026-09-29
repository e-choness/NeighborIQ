<script setup lang="ts">
import { Search, X } from '@lucide/vue'
import { useQuery } from '@pinia/colada'
import { refDebounced } from '@vueuse/core'
import { computed, onMounted, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sheet from '@/components/shell/Sheet.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import { inputClass } from '@/components/ui/inputClass'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'
import { beds, moneyShort, pct, PROPERTY_TYPE_LABEL } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { ListingPage } from '@/lib/types'
import { useCity } from '@/stores/city'
import { useMapStage, type BBox } from '@/stores/mapStage'
import { useShell } from '@/stores/shell'

const route = useRoute()
const router = useRouter()
const cities = useCity()
const stage = useMapStage()
const shell = useShell()

const SORTS = {
  yield: { label: 'Highest yield', sort: 'gross_yield', order: 'desc' },
  ppsf: { label: 'Lowest $/sq ft', sort: 'price_per_sqft', order: 'asc' },
  newest: { label: 'Newest', sort: 'listed_at', order: 'desc' },
  price: { label: 'Lowest price', sort: 'price', order: 'asc' },
} as const
type SortKey = keyof typeof SORTS

const q = route.query
const filters = reactive({
  q: (q.q as string) ?? '',
  types: ((q.types as string) ?? '').split(',').filter(Boolean),
  bedsMin: q.beds ? Number(q.beds) : null as number | null,
  priceMax: q.max ? Number(q.max) : null as number | null,
  priceCut: q.cut === '1',
  sort: ((q.sort as SortKey) ?? 'yield') as SortKey,
  bbox: q.bbox ? ((q.bbox as string).split(',').map(Number) as BBox) : null,
})

// A new city (top bar) starts a new search area; the store clears ?bbox, mirror that here
watch(() => route.query.bbox, (b) => {
  if (!b) filters.bbox = null
})

// Keep the URL shareable, and remember it so a listing's back button restores these filters
watch([filters, () => cities.city], () => {
  const f = filters
  const query = {
    city: cities.city || undefined, q: f.q || undefined, types: f.types.join(',') || undefined,
    beds: f.bedsMin ?? undefined, max: f.priceMax ?? undefined, cut: f.priceCut ? '1' : undefined,
    sort: f.sort === 'yield' ? undefined : f.sort,
    bbox: f.bbox?.map((v) => v.toFixed(5)).join(','),
  }
  router.replace({ query })
  shell.exploreQuery = Object.fromEntries(Object.entries(query).filter(([, v]) => v !== undefined).map(([k, v]) => [k, String(v)]))
}, { deep: true, immediate: true })

const params = computed(() => {
  const s = SORTS[filters.sort]
  const [w, sLat, e, n] = filters.bbox ?? []
  return {
    city: cities.city, q: filters.q, property_type: filters.types.join(','), rooms_min: filters.bedsMin,
    price_max: filters.priceMax, price_cut: filters.priceCut || undefined, sort: s.sort, order: s.order,
    min_lon: w, min_lat: sLat, max_lon: e, max_lat: n, page_size: 200,
  }
})
const debouncedParams = refDebounced(computed(() => JSON.stringify(params.value)), 200)
const { data: page, isLoading } = useQuery({
  key: () => ['listings', debouncedParams.value],
  query: () => api<ListingPage>('/houses', { query: JSON.parse(debouncedParams.value) }),
  enabled: () => Boolean(cities.city),
  placeholderData: (prev: ListingPage | undefined) => prev,
})

onMounted(() => stage.show('explore', { bbox: filters.bbox }))
watch(() => page.value?.items, (items) => (stage.listings = items ?? []), { immediate: true })
watch(() => filters.bbox, (b) => (stage.bbox = b))
watch(() => stage.areaRequest, (b) => {
  if (!b) return
  filters.bbox = b
  stage.areaRequest = null
})

// One notice when a whole city is demo data; per-row badges only when real and synthetic mix
const allSynthetic = computed(() => (cities.market?.synthetic_share_pct ?? 0) >= 100)
function toggleType(t: string) {
  filters.types = filters.types.includes(t) ? filters.types.filter((x) => x !== t) : [...filters.types, t]
}
function reset() {
  Object.assign(filters, { types: [], bedsMin: null, priceMax: null, priceCut: false, q: '', bbox: null })
}
const selectClass = cn(inputClass, 'h-9 rounded-[10px] px-2 text-[13px]')
</script>

<template>
  <Sheet side="left" :label="`${cities.city} listings`" body-class="px-2 py-1.5">
    <template #header>
      <div class="flex shrink-0 flex-col gap-2.5 border-b border-border px-[18px] pb-3.5 pt-[18px]">
        <div class="flex items-baseline justify-between gap-3">
          <h1 class="font-display text-[30px] tracking-[0.03em]">{{ cities.city }} listings</h1>
          <span class="num whitespace-nowrap text-xs text-muted" aria-live="polite">
            <template v-if="page">{{ page.total.toLocaleString('en-CA') }} listings</template>
          </span>
        </div>
        <div class="relative">
          <Search class="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" />
          <input v-model="filters.q" :class="cn(inputClass, 'pl-9')" placeholder="Neighbourhood or street" aria-label="Search" />
        </div>
        <div class="flex flex-wrap gap-1.5" role="group" aria-label="Property type">
          <button
            v-for="(label, t) in PROPERTY_TYPE_LABEL"
            :key="t"
            type="button"
            :aria-pressed="filters.types.includes(t)"
            class="whitespace-nowrap rounded-[9px] border px-2.5 py-[5px] text-xs transition-colors"
            :class="filters.types.includes(t) ? 'border-accent bg-accent-soft text-accent' : 'border-border text-text-2 hover:text-text'"
            @click="toggleType(t)"
          >
            {{ label }}
          </button>
        </div>
        <div class="grid grid-cols-3 gap-1.5">
          <select v-model.number="filters.bedsMin" :class="selectClass" aria-label="Minimum bedrooms">
            <option :value="null">Any beds</option>
            <option v-for="n in [1, 2, 3, 4]" :key="n" :value="n">{{ n }}+ beds</option>
          </select>
          <select v-model.number="filters.priceMax" :class="selectClass" aria-label="Maximum price">
            <option :value="null">Any price</option>
            <option v-for="p in [400000, 600000, 800000, 1000000, 1500000, 2000000]" :key="p" :value="p">≤ {{ moneyShort(p) }}</option>
          </select>
          <select v-model="filters.sort" :class="selectClass" aria-label="Sort">
            <option v-for="(s, k) in SORTS" :key="k" :value="k">{{ s.label }}</option>
          </select>
        </div>
        <label class="flex cursor-pointer items-center gap-2 text-xs text-text-2">
          <input v-model="filters.priceCut" type="checkbox" /> Price reduced only
        </label>
        <p v-if="allSynthetic" class="text-[11px] text-muted"><span class="text-warn">Demo data:</span> every {{ cities.city }} listing here is synthetic.</p>
        <div v-if="filters.bbox" class="flex items-center justify-between rounded-[10px] bg-accent-soft px-3 py-[7px] text-xs text-accent">
          Showing the selected map area
          <button type="button" class="flex items-center gap-1 hover:underline" @click="filters.bbox = null"><X class="h-3.5 w-3.5" /> Clear</button>
        </div>
      </div>
    </template>

    <ol :class="{ 'opacity-60': isLoading && page }">
      <template v-if="!page">
        <li v-for="i in 6" :key="i" class="p-3"><Skeleton class="h-14" /></li>
      </template>
      <li v-else-if="!page.items.length" class="px-2.5 py-8 text-center text-sm text-text-2">
        No listings match. <Button variant="ghost" size="sm" @click="reset">Reset filters</Button>
      </li>
      <li v-for="l in page?.items" :key="l.id">
        <button
          type="button"
          class="grid w-full grid-cols-[1fr_auto] gap-x-4 gap-y-1 rounded-[14px] px-3 py-[11px] text-left transition-colors hover:bg-seg-on focus-visible:bg-seg-on"
          :class="{ 'bg-seg-on': stage.highlightId === l.id }"
          @mouseenter="stage.highlightId = l.id"
          @mouseleave="stage.highlightId = null"
          @click="router.push(`/listings/${l.id}`)"
        >
          <span class="num text-base font-medium">{{ moneyShort(l.price) }}</span>
          <span class="num text-right text-sm" :class="l.gross_yield_pct ? 'text-text' : 'text-muted'">
            {{ pct(l.gross_yield_pct) }} <span class="text-[11px] text-muted">yield</span>
          </span>
          <span class="truncate text-xs text-text-2">
            {{ beds(l.rooms) }} · {{ l.bathrooms ?? '—' }} ba · {{ l.sqft?.toLocaleString('en-CA') ?? '—' }} sq ft · {{ l.community }}
          </span>
          <span class="num text-right text-xs text-muted">${{ l.price_per_sqft ? Math.round(l.price_per_sqft) : '—' }}/sq ft</span>
          <span
            v-if="l.price_cut_pct || (l.days_on_market !== null && l.days_on_market > 45) || (l.is_synthetic && !allSynthetic)"
            class="col-span-2 flex flex-wrap gap-1.5"
          >
            <Badge v-if="l.price_cut_pct" tone="accent">−{{ pct(l.price_cut_pct) }}</Badge>
            <Badge v-if="l.days_on_market !== null && l.days_on_market > 45" tone="neutral">{{ l.days_on_market }} days</Badge>
            <Badge v-if="l.is_synthetic && !allSynthetic" tone="warn">Synthetic</Badge>
          </span>
        </button>
      </li>
    </ol>
  </Sheet>
</template>
