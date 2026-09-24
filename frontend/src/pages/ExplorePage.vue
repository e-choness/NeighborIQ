<script setup lang="ts">
import { Search, X } from '@lucide/vue'
import { useQuery } from '@pinia/colada'
import { refDebounced } from '@vueuse/core'
import { computed, defineAsyncComponent, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import { inputClass } from '@/components/ui/inputClass'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'
import { beds, moneyShort, pct, PROPERTY_TYPE_LABEL } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { ListingPage, Market } from '@/lib/types'

const ListingsMap = defineAsyncComponent(() => import('@/components/map/ListingsMap.vue'))
const route = useRoute()
const router = useRouter()

const { data: markets } = useQuery({ key: ['markets'], query: () => api<Market[]>('/markets') })

const SORTS = {
  yield: { label: 'Highest yield', sort: 'gross_yield', order: 'desc' },
  ppsf: { label: 'Lowest $/sq ft', sort: 'price_per_sqft', order: 'asc' },
  newest: { label: 'Newest', sort: 'listed_at', order: 'desc' },
  price: { label: 'Lowest price', sort: 'price', order: 'asc' },
} as const
type SortKey = keyof typeof SORTS

const q = route.query
const filters = reactive({
  city: (q.city as string) ?? '',
  q: (q.q as string) ?? '',
  types: ((q.types as string) ?? '').split(',').filter(Boolean),
  bedsMin: q.beds ? Number(q.beds) : null as number | null,
  priceMax: q.max ? Number(q.max) : null as number | null,
  priceCut: q.cut === '1',
  sort: ((q.sort as SortKey) ?? 'yield') as SortKey,
  bbox: q.bbox ? ((q.bbox as string).split(',').map(Number) as [number, number, number, number]) : null,
})
watch(markets, (m) => {
  if (!filters.city && m?.length) filters.city = m[0].city
}, { immediate: true })

// Keep the URL shareable
watch(filters, (f) => {
  router.replace({
    query: {
      city: f.city || undefined, q: f.q || undefined, types: f.types.join(',') || undefined,
      beds: f.bedsMin ?? undefined, max: f.priceMax ?? undefined, cut: f.priceCut ? '1' : undefined,
      sort: f.sort === 'yield' ? undefined : f.sort,
      bbox: f.bbox?.map((v) => v.toFixed(5)).join(','),
    },
  })
}, { deep: true })

const params = computed(() => {
  const s = SORTS[filters.sort]
  const [w, sLat, e, n] = filters.bbox ?? []
  return {
    city: filters.city, q: filters.q, property_type: filters.types.join(','), rooms_min: filters.bedsMin,
    price_max: filters.priceMax, price_cut: filters.priceCut || undefined, sort: s.sort, order: s.order,
    min_lon: w, min_lat: sLat, max_lon: e, max_lat: n, page_size: 200,
  }
})
const debouncedParams = refDebounced(computed(() => JSON.stringify(params.value)), 200)
const { data: page, isLoading } = useQuery({
  key: () => ['listings', debouncedParams.value],
  query: () => api<ListingPage>('/houses', { query: JSON.parse(debouncedParams.value) }),
  enabled: () => Boolean(filters.city),
  placeholderData: (prev: ListingPage | undefined) => prev,
})

const { data: communities } = useQuery({
  key: () => ['communities', filters.city],
  query: () => api<{ items: { name: string; latitude: number | null; longitude: number | null }[] }>('/communities', { query: { city: filters.city } }),
  enabled: () => Boolean(filters.city),
})
const labels = computed(() =>
  (communities.value?.items ?? []).flatMap((c) =>
    c.latitude !== null && c.longitude !== null ? [{ name: c.name, latitude: c.latitude, longitude: c.longitude }] : [],
  ),
)
const hovered = ref<number | null>(null)
const market = computed(() => markets.value?.find((m) => m.city === filters.city))
// One notice when a whole city is demo data; per-row badges only when real and synthetic mix
const allSynthetic = computed(() => (market.value?.synthetic_share_pct ?? 0) >= 100)
function toggleType(t: string) {
  filters.types = filters.types.includes(t) ? filters.types.filter((x) => x !== t) : [...filters.types, t]
}
function open(id: number) {
  router.push(`/listings/${id}`)
}
</script>

<template>
  <div class="flex h-dvh flex-col pt-[4.5rem] lg:flex-row">
    <!-- Filters + results -->
    <section class="flex max-h-[55dvh] flex-col border-border lg:h-full lg:max-h-none lg:w-[26rem] lg:shrink-0 lg:border-r">
      <div class="space-y-3 border-b border-border p-4">
        <div class="flex gap-2">
          <select v-model="filters.city" :class="cn(inputClass, 'w-36 shrink-0')" aria-label="City" @change="filters.bbox = null">
            <option v-for="m in markets" :key="m.city" :value="m.city">{{ m.city }}</option>
          </select>
          <div class="relative flex-1">
            <Search class="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" />
            <input v-model="filters.q" :class="cn(inputClass, 'pl-9')" placeholder="Neighbourhood or street" aria-label="Search" />
          </div>
        </div>
        <div class="flex flex-wrap gap-1.5" role="group" aria-label="Property type">
          <button
            v-for="(label, t) in PROPERTY_TYPE_LABEL"
            :key="t"
            :aria-pressed="filters.types.includes(t)"
            class="rounded-md border px-2.5 py-1 text-xs transition-colors"
            :class="filters.types.includes(t) ? 'border-accent bg-accent-soft text-accent' : 'border-border text-text-2 hover:text-text'"
            @click="toggleType(t)"
          >
            {{ label }}
          </button>
        </div>
        <div class="grid grid-cols-3 gap-2">
          <select v-model.number="filters.bedsMin" :class="inputClass" aria-label="Minimum bedrooms">
            <option :value="null">Any beds</option>
            <option v-for="n in [1, 2, 3, 4]" :key="n" :value="n">{{ n }}+ beds</option>
          </select>
          <select v-model.number="filters.priceMax" :class="inputClass" aria-label="Maximum price">
            <option :value="null">Any price</option>
            <option v-for="p in [400000, 600000, 800000, 1000000, 1500000, 2000000]" :key="p" :value="p">≤ {{ moneyShort(p) }}</option>
          </select>
          <select v-model="filters.sort" :class="inputClass" aria-label="Sort">
            <option v-for="(s, k) in SORTS" :key="k" :value="k">{{ s.label }}</option>
          </select>
        </div>
        <div class="flex items-center justify-between text-xs">
          <label class="flex cursor-pointer items-center gap-2 text-text-2">
            <input v-model="filters.priceCut" type="checkbox" class="accent-[var(--accent)]" /> Price reduced only
          </label>
          <span class="text-muted" aria-live="polite">
            <template v-if="page">{{ page.total.toLocaleString('en-CA') }} listings</template>
          </span>
        </div>
        <p v-if="allSynthetic" class="text-[11px] text-muted"><span class="text-warn">Demo data:</span> every {{ filters.city }} listing here is synthetic.</p>
        <div v-if="filters.bbox" class="flex items-center justify-between rounded-lg bg-accent-soft px-3 py-1.5 text-xs text-accent">
          Showing the selected map area
          <button class="flex items-center gap-1 hover:underline" @click="filters.bbox = null"><X class="h-3 w-3" /> Clear</button>
        </div>
      </div>

      <ol class="flex-1 overflow-y-auto" :class="{ 'opacity-60': isLoading && page }">
        <template v-if="!page">
          <li v-for="i in 6" :key="i" class="p-4"><Skeleton class="h-14" /></li>
        </template>
        <li v-else-if="!page.items.length" class="p-8 text-center text-sm text-text-2">
          No listings match. <Button variant="ghost" size="sm" @click="Object.assign(filters, { types: [], bedsMin: null, priceMax: null, priceCut: false, q: '', bbox: null })">Reset filters</Button>
        </li>
        <li v-for="l in page?.items" :key="l.id">
          <button
            class="grid w-full grid-cols-[1fr_auto] gap-x-4 gap-y-1 border-b border-border px-4 py-3 text-left transition-colors hover:bg-surface-2 focus-visible:bg-surface-2"
            :class="{ 'bg-surface-2': hovered === l.id }"
            @mouseenter="hovered = l.id"
            @mouseleave="hovered = null"
            @click="open(l.id)"
          >
            <span class="num text-base font-medium">{{ moneyShort(l.price) }}</span>
            <span class="num text-right text-sm" :class="l.gross_yield_pct ? 'text-text' : 'text-muted'">
              {{ pct(l.gross_yield_pct) }} <span class="text-xs text-muted">yield</span>
            </span>
            <span class="truncate text-xs text-text-2">
              {{ beds(l.rooms) }} · {{ l.bathrooms ?? '—' }} ba · {{ l.sqft?.toLocaleString('en-CA') ?? '—' }} sq ft · {{ l.community }}
            </span>
            <span class="num text-right text-xs text-muted">${{ l.price_per_sqft ? Math.round(l.price_per_sqft) : '—' }}/sq ft</span>
            <span class="col-span-2 flex flex-wrap gap-1.5">
              <Badge v-if="l.price_cut_pct" tone="accent">−{{ pct(l.price_cut_pct) }}</Badge>
              <Badge v-if="l.days_on_market !== null && l.days_on_market > 45" tone="neutral">{{ l.days_on_market }} days</Badge>
              <Badge v-if="l.is_synthetic && !allSynthetic" tone="warn">Synthetic</Badge>
            </span>
          </button>
        </li>
      </ol>
    </section>

    <!-- Map -->
    <section class="relative min-h-0 flex-1">
      <ListingsMap
        v-if="page"
        :listings="page.items"
        :highlight="hovered"
        :bbox="filters.bbox"
        :labels="labels"
        @hover="hovered = $event"
        @open="open"
        @search-area="filters.bbox = $event"
      />
    </section>
  </div>
</template>
