<script setup lang="ts">
import { ArrowRight } from '@lucide/vue'
import { useQuery } from '@pinia/colada'
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import Button from '@/components/ui/Button.vue'
import Segmented from '@/components/ui/Segmented.vue'
import Stat from '@/components/ui/Stat.vue'
import { api } from '@/lib/api'
import { moneyShort, pct } from '@/lib/format'
import { HEX_METRICS, type HexMetric } from '@/lib/metrics'
import { theme } from '@/lib/theme'
import type { Market, MarketPoints } from '@/lib/types'
import { SEQUENTIAL } from '@/theme/palette'

const HexMap3D = defineAsyncComponent(() => import('@/components/map/HexMap3D.vue'))
const router = useRouter()

const { data: markets, isLoading: marketsLoading } = useQuery({
  key: ['markets'],
  query: () => api<Market[]>('/markets'),
})

const city = ref<string>('')
watch(markets, (m) => {
  if (m?.length && !m.some((x) => x.city === city.value)) city.value = m[0].city
}, { immediate: true })

const market = computed(() => markets.value?.find((m) => m.city === city.value) ?? null)

const { data: points } = useQuery({
  key: () => ['market-points', city.value],
  query: () => api<MarketPoints>(`/markets/${encodeURIComponent(city.value)}/points`),
  enabled: () => Boolean(city.value),
})

const { data: communities } = useQuery({
  key: () => ['communities', city.value],
  query: () =>
    api<{ items: { name: string; latitude: number | null; longitude: number | null }[] }>('/communities', {
      query: { city: city.value },
    }),
  enabled: () => Boolean(city.value),
})
const labels = computed(() =>
  (communities.value?.items ?? [])
    .filter((c) => c.latitude !== null && c.longitude !== null)
    .map((c) => ({ name: c.name, latitude: c.latitude!, longitude: c.longitude! })),
)

const metric = ref<HexMetric>('gross_yield_pct')
const metricOptions = (Object.keys(HEX_METRICS) as HexMetric[]).map((value) => ({ value, label: HEX_METRICS[value].short }))
const range = ref<[number, number]>([0, 1])
const legendGradient = computed(() => `linear-gradient(90deg, ${SEQUENTIAL[theme.value].join(', ')})`)

const center = computed<[number, number] | null>(() =>
  market.value?.longitude && market.value.latitude ? [market.value.longitude, market.value.latitude] : null,
)

function openArea([w, s, e, n]: [number, number, number, number]) {
  router.push({ path: '/explore', query: { city: city.value, bbox: [w, s, e, n].map((v) => v.toFixed(5)).join(',') } })
}
</script>

<template>
  <div class="relative h-dvh w-full overflow-hidden bg-surface">
    <HexMap3D
      v-if="points"
      :points="points"
      :metric="metric"
      :center="center"
      :labels="labels"
      :pad-left="480"
      @domain="range = $event"
      @select="openArea"
    />

    <!-- Overlay: one question, the numbers that answer it, two next steps -->
    <section class="pointer-events-none absolute inset-x-0 top-0 flex h-full flex-col justify-end p-3 pt-20 sm:justify-start sm:p-6 sm:pt-24">
      <div class="glass pointer-events-auto max-h-[52dvh] w-full max-w-md overflow-y-auto rounded-2xl p-5 shadow-2xl sm:max-h-none sm:overflow-visible">
        <div v-if="marketsLoading" class="text-sm text-muted">Loading markets…</div>

        <div v-else-if="!markets?.length">
          <h1 class="text-xl font-semibold tracking-tight">No listings loaded yet</h1>
          <p class="mt-2 text-sm text-text-2">
            Start the stack with <code class="num text-xs">docker compose up</code> — the bootstrap step loads demo data —
            or load data from the admin page.
          </p>
        </div>

        <template v-else>
          <div class="-mx-1 mb-4 flex flex-wrap gap-1" role="tablist" aria-label="City">
            <button
              v-for="m in markets"
              :key="m.city"
              role="tab"
              :aria-selected="m.city === city"
              class="rounded-md px-2.5 py-1 text-xs transition-colors"
              :class="m.city === city ? 'bg-surface-2 text-text' : 'text-muted hover:text-text-2'"
              @click="city = m.city"
            >
              {{ m.city }}
            </button>
          </div>

          <h1 class="text-xl font-semibold sm:text-2xl leading-tight tracking-tight">
            {{ HEX_METRICS[metric].label }} across {{ city }}
          </h1>
          <p class="mt-2 hidden text-sm leading-relaxed text-text-2 sm:block">
            Each column covers ~0.7 km². Height and colour show the median of the
            {{ market?.listing_count.toLocaleString('en-CA') }} active listings inside it — taller means
            {{ HEX_METRICS[metric].higherIs }}. Select a column to see its listings.
          </p>

          <div class="mt-4 flex flex-wrap items-center gap-3">
            <Segmented v-model="metric" :options="metricOptions" label="Map metric" />
          </div>

          <div class="mt-3" aria-hidden="true">
            <div class="h-1.5 rounded-full" :style="{ background: legendGradient }" />
            <div class="num mt-1 flex justify-between text-[11px] text-muted">
              <span>{{ HEX_METRICS[metric].format(range[0]) }}</span>
              <span>{{ HEX_METRICS[metric].format(range[1]) }}</span>
            </div>
          </div>

          <dl v-if="market" class="mt-5 grid grid-cols-3 gap-x-4 gap-y-4 border-t border-border pt-4">
            <Stat label="Median asking" :value="moneyShort(market.median_price)" />
            <Stat label="Median $/sq ft" :value="moneyShort(market.median_price_per_sqft)" />
            <Stat label="Gross yield" :value="pct(market.median_gross_yield_pct)" />
            <Stat label="Cap rate" :value="pct(market.median_cap_rate_pct)" />
            <Stat label="With price cuts" :value="pct(market.price_cut_share_pct, 0)" />
            <Stat label="Median days listed" :value="market.median_days_on_market?.toString() ?? '—'" />
          </dl>

          <div class="mt-5 flex flex-wrap gap-2">
            <Button to="/analyze">Analyze a property <ArrowRight class="h-4 w-4" /></Button>
            <Button :to="{ path: '/explore', query: { city } }" variant="secondary">Browse {{ city }} listings</Button>
          </div>

          <p v-if="market && market.synthetic_share_pct > 0" class="mt-4 text-[11px] leading-snug text-muted">
            <span class="text-warn">Demo data.</span>
            {{ Math.round(market.synthetic_share_pct) }}% of these listings are synthetic —
            <RouterLink to="/data" class="underline decoration-dotted underline-offset-2 hover:text-text-2">what's real</RouterLink>.
          </p>
        </template>
      </div>
    </section>
  </div>
</template>
