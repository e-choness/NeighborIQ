<script setup lang="ts">
/** One question (what does this city look like on my metric?), the numbers that answer it, two next steps. */
import { ArrowRight, Building2, Percent, Tag, TrendingDown } from '@lucide/vue'
import { useQuery } from '@pinia/colada'
import { computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import Sheet from '@/components/shell/Sheet.vue'
import Button from '@/components/ui/Button.vue'
import Segmented from '@/components/ui/Segmented.vue'
import { api } from '@/lib/api'
import { beds, money, moneyShort, pct, PROPERTY_TYPE_LABEL } from '@/lib/format'
import { HEX_METRICS, type HexMetric } from '@/lib/metrics'
import { theme } from '@/lib/theme'
import type { ListingPage } from '@/lib/types'
import { isPhone, showBestRow, showStatTiles } from '@/lib/viewport'
import { useCity } from '@/stores/city'
import { useMapStage } from '@/stores/mapStage'
import { SEQUENTIAL } from '@/theme/palette'

const cities = useCity()
const stage = useMapStage()
const router = useRouter()
onMounted(() => stage.show('home'))

const market = computed(() => cities.market)
const metricOptions = (Object.keys(HEX_METRICS) as HexMetric[]).map((value) => ({ value, label: HEX_METRICS[value].short }))
const metric = computed({ get: () => stage.metric, set: (v: HexMetric) => (stage.metric = v) })
const legendGradient = computed(() => `linear-gradient(90deg, ${SEQUENTIAL[theme.value].join(', ')})`)

const { data: best } = useQuery({
  key: () => ['best-yields', cities.city],
  query: () => api<ListingPage>('/houses', { query: { city: cities.city, sort: 'gross_yield', order: 'desc', page_size: 3 } }),
  enabled: () => Boolean(cities.city),
})
const bestCards = computed(() =>
  (best.value?.items ?? []).map((l, i) => ({
    id: l.id,
    rank: `0${i + 1}`,
    price: moneyShort(l.price),
    yield: pct(l.gross_yield_pct),
    meta: [
      `${beds(l.rooms)} ${l.property_type ? PROPERTY_TYPE_LABEL[l.property_type].toLowerCase() : ''}`.trim(),
      l.community,
    ].filter(Boolean).join(' · '),
  })),
)
const bestInSheet = computed(() => isPhone.value || !showBestRow.value)

const stats = computed(() => {
  const m = market.value
  if (!m) return []
  const all = [
    { label: 'Median asking', value: moneyShort(m.median_price) },
    { label: 'Gross yield', value: pct(m.median_gross_yield_pct) },
    { label: 'With price cuts', value: pct(m.price_cut_share_pct, 0) },
    { label: 'Median $/sq ft', value: money(m.median_price_per_sqft) },
    { label: 'Cap rate', value: pct(m.median_cap_rate_pct) },
    { label: 'Days listed', value: m.median_days_on_market?.toString() ?? '—' },
  ]
  // The first three move to the floating tiles when there is room for them
  return isPhone.value || !showStatTiles.value ? all : all.slice(3)
})
const tiles = computed(() => {
  const m = market.value
  if (!m) return []
  return [
    { icon: Tag, value: moneyShort(m.median_price), label: 'Median asking' },
    { icon: Percent, value: pct(m.median_gross_yield_pct), label: 'Median gross yield' },
    { icon: TrendingDown, value: pct(m.price_cut_share_pct, 0), label: 'Listings with price cuts' },
  ]
})
</script>

<template>
  <Sheet side="left" fit label="Map overview" body-class="px-[22px] pb-5 pt-[22px]">
    <div v-if="cities.isLoading" class="text-sm text-muted">Loading markets…</div>

    <div v-else-if="!cities.markets?.length">
      <h1 class="font-display text-[30px] leading-tight tracking-[0.02em]">No listings loaded yet</h1>
      <p class="mt-2 text-sm text-text-2">
        Start the stack with <code class="num text-xs">docker compose up</code> — the bootstrap step loads demo data —
        or load data from the admin tab on the Data screen.
      </p>
    </div>

    <template v-else>
      <p class="num text-[11px] uppercase tracking-[0.12em] text-muted">
        {{ cities.city }} · {{ market?.listing_count.toLocaleString('en-CA') }} active listings
      </p>
      <h1 class="font-display mt-3 text-[34px] uppercase leading-[1.04] tracking-[0.03em]">
        <span class="block">{{ HEX_METRICS[metric].label }}</span>
        <span class="block text-accent">across {{ cities.city }}</span>
      </h1>
      <p class="mt-3 text-sm leading-relaxed text-text-2 [text-wrap:pretty]">
        Each column covers ~0.7 km². Height and colour show the median of the listings inside it — taller means
        {{ HEX_METRICS[metric].higherIs }}. Select a column to see its listings.
      </p>

      <Segmented v-model="metric" :options="metricOptions" label="Map metric" class="mt-4" />

      <div class="mt-3.5" aria-hidden="true">
        <div class="h-1.5 rounded-full" :style="{ background: legendGradient }" />
        <div class="num mt-[5px] flex justify-between text-[11px] text-muted">
          <span>{{ HEX_METRICS[metric].format(stage.range[0]) }}</span>
          <span>{{ HEX_METRICS[metric].format(stage.range[1]) }}</span>
        </div>
      </div>

      <dl v-if="market" class="mt-[18px] grid grid-cols-3 gap-x-3 gap-y-3.5 border-t border-border pt-4">
        <div v-for="s in stats" :key="s.label" class="min-w-0">
          <dt class="text-xs text-muted">{{ s.label }}</dt>
          <dd class="num mt-1 truncate text-[17px] font-medium">{{ s.value }}</dd>
        </div>
      </dl>

      <div class="mt-[18px] flex flex-wrap gap-2">
        <Button to="/analyze">Analyze a property <ArrowRight class="h-4 w-4" /></Button>
        <Button :to="{ path: '/explore', query: { city: cities.city } }" variant="secondary">Browse {{ cities.city }} listings</Button>
      </div>

      <p v-if="market && market.synthetic_share_pct > 0" class="mt-3.5 text-[11px] leading-snug text-muted">
        <span class="text-warn">Demo data.</span>
        {{ Math.round(market.synthetic_share_pct) }}% of these listings are synthetic —
        <RouterLink to="/data" class="text-text-2 underline decoration-dotted underline-offset-2 hover:text-text">what's real</RouterLink>.
      </p>

      <template v-if="bestInSheet && bestCards.length">
        <p class="eyebrow mt-5">Best yields in {{ cities.city }}</p>
        <div class="mt-2 flex flex-col gap-2">
          <button
            v-for="b in bestCards"
            :key="b.id"
            type="button"
            class="flex items-center gap-3 rounded-[14px] border border-border bg-surface-2 p-3 text-left hover:bg-seg-on"
            @click="router.push(`/listings/${b.id}`)"
          >
            <span class="grid h-[34px] w-[34px] shrink-0 place-items-center rounded-[10px] bg-surface-2 text-accent">
              <Building2 class="h-[18px] w-[18px]" :stroke-width="1.75" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="num block text-[15px] font-medium">{{ b.price }} <span class="text-xs text-accent">{{ b.yield }} yield</span></span>
              <span class="block truncate text-xs text-text-2">{{ b.meta }}</span>
            </span>
            <ArrowRight class="h-3.5 w-3.5 text-text-2" />
          </button>
        </div>
      </template>
    </template>
  </Sheet>

  <!-- Desktop-only floating widgets -->
  <div v-if="!isPhone && showStatTiles && market" class="absolute right-3 top-[76px] z-10 flex w-[204px] flex-col gap-2.5">
    <div v-for="t in tiles" :key="t.label" class="glass flex items-center gap-3 rounded-[18px] p-3.5">
      <span class="grid h-[38px] w-[38px] shrink-0 place-items-center rounded-xl border border-border bg-surface-2 text-accent">
        <component :is="t.icon" class="h-[18px] w-[18px]" :stroke-width="1.75" aria-hidden="true" />
      </span>
      <div class="min-w-0">
        <div class="num text-[21px] font-medium tracking-[-0.02em]">{{ t.value }}</div>
        <div class="mt-0.5 text-xs text-muted">{{ t.label }}</div>
      </div>
    </div>
  </div>

  <div v-if="!isPhone && showBestRow && bestCards.length" class="absolute bottom-3 left-[500px] right-[228px] z-10 grid grid-cols-3 gap-3">
    <button
      v-for="b in bestCards"
      :key="b.id"
      type="button"
      class="glass flex flex-col gap-2.5 rounded-[18px] p-4 text-left text-text"
      @click="router.push(`/listings/${b.id}`)"
    >
      <span class="flex w-full items-center gap-3">
        <span class="hidden h-[38px] w-[38px] shrink-0 min-[1440px]:grid place-items-center rounded-xl border border-border bg-surface-2 text-accent">
          <Building2 class="h-[18px] w-[18px]" :stroke-width="1.75" aria-hidden="true" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="block text-[11px] uppercase tracking-[0.08em] text-muted">Best yield · {{ b.rank }}</span>
          <span class="num mt-0.5 block whitespace-nowrap text-[17px] font-medium">{{ b.price }} <span class="text-[13px] text-accent">{{ b.yield }}<span class="hidden min-[1440px]:inline"> yield</span></span></span>
        </span>
      </span>
      <span class="flex w-full items-center gap-2.5">
        <span class="min-w-0 flex-1 truncate text-xs text-text-2">{{ b.meta }}</span>
        <span class="grid h-7 w-7 place-items-center rounded-full border border-border text-text-2">
          <ArrowRight class="h-3.5 w-3.5" aria-hidden="true" />
        </span>
      </span>
    </button>
  </div>
</template>
