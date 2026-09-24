<script setup lang="ts">
import { ArrowLeft, Bookmark, BookmarkCheck } from '@lucide/vue'
import { useMutation, useQuery, useQueryCache } from '@pinia/colada'
import { computed, defineAsyncComponent, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import CashFlowPanel from '@/components/analysis/CashFlowPanel.vue'
import FairValue from '@/components/analysis/FairValue.vue'
import NeighbourhoodFacts from '@/components/analysis/NeighbourhoodFacts.vue'
import PriceHistory from '@/components/analysis/PriceHistory.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Panel from '@/components/ui/Panel.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import Stat from '@/components/ui/Stat.vue'
import { api, ApiError } from '@/lib/api'
import { beds, money, moneyShort, pct, PROPERTY_TYPE_LABEL, signedPct } from '@/lib/format'
import type { CashFlowInput, Insights, Listing, Market, Neighbourhood, PricePoint, SavedDeal } from '@/lib/types'
import { useAuth } from '@/stores/auth'

const CompsMap = defineAsyncComponent(() => import('@/components/map/CompsMap.vue'))
const props = defineProps<{ id: number }>()
const auth = useAuth()
const router = useRouter()
const cache = useQueryCache()

const { data: listing, error } = useQuery({ key: () => ['listing', props.id], query: () => api<Listing>(`/houses/${props.id}`) })
const { data: insights } = useQuery({ key: () => ['insights', props.id], query: () => api<Insights>(`/houses/${props.id}/insights`) })
const { data: history } = useQuery({
  key: () => ['price-history', props.id],
  query: () => api<{ items: PricePoint[] }>(`/houses/${props.id}/price-history`),
})
const { data: places } = useQuery({ key: () => ['neighbourhood', props.id], query: () => api<Neighbourhood>(`/houses/${props.id}/neighbourhood`) })
const { data: markets } = useQuery({
  key: () => ['markets', listing.value?.city ?? ''],
  query: () => api<Market[]>('/markets', { query: { city: listing.value!.city } }),
  enabled: () => Boolean(listing.value),
})
const market = computed(() => markets.value?.[0] ?? null)

const { data: saved } = useQuery({
  key: ['portfolio'],
  query: () => api<SavedDeal[]>('/portfolio/saved'),
  enabled: () => auth.isAuthenticated,
})
const isSaved = computed(() => saved.value?.some((d) => d.house_id === props.id) ?? false)
const assumptions = ref<CashFlowInput | null>(null)

const { mutate: toggleSave, isLoading: saving } = useMutation({
  mutation: async () => {
    if (!auth.isAuthenticated) {
      router.push({ name: 'login', query: { next: `/listings/${props.id}` } })
      return
    }
    if (isSaved.value) return api(`/portfolio/saved/${props.id}`, { method: 'DELETE' })
    return api('/portfolio/save', { method: 'POST', body: { house_id: props.id, assumptions: assumptions.value } })
  },
  onSettled: () => cache.invalidateQueries({ key: ['portfolio'] }),
})

const notFound = computed(() => error.value instanceof ApiError && error.value.status === 404)
const facts = computed(() => {
  const l = listing.value
  if (!l) return []
  return [
    { label: 'Type', value: l.property_type ? PROPERTY_TYPE_LABEL[l.property_type] : '—' },
    { label: 'Bedrooms', value: beds(l.rooms) },
    { label: 'Bathrooms', value: l.bathrooms?.toString() ?? '—' },
    { label: 'Size', value: l.sqft ? `${l.sqft.toLocaleString('en-CA')} sq ft` : '—' },
    { label: '$/sq ft', value: l.price_per_sqft ? `$${Math.round(l.price_per_sqft)}` : '—' },
    { label: 'Condo fee', value: l.condo_fee ? `${money(l.condo_fee)}/mo` : 'None' },
    { label: 'Property tax', value: l.property_tax ? `${money(l.property_tax)}/yr` : '—' },
    { label: 'Built', value: l.age !== null ? `${new Date().getFullYear() - l.age}` : '—' },
  ]
})
</script>

<template>
  <div v-if="notFound" class="py-24 text-center">
    <p class="text-lg font-medium">This listing is no longer available.</p>
    <Button to="/explore" variant="secondary" class="mt-4">Browse listings</Button>
  </div>

  <div v-else-if="!listing" class="space-y-4">
    <Skeleton class="h-8 w-2/3" />
    <Skeleton class="h-40" />
  </div>

  <article v-else>
    <RouterLink :to="{ path: '/explore', query: { city: listing.city } }" class="inline-flex items-center gap-1.5 text-xs text-text-2 hover:text-text">
      <ArrowLeft class="h-3.5 w-3.5" /> {{ listing.city }} listings
    </RouterLink>

    <header class="mt-4 flex flex-wrap items-start justify-between gap-6">
      <div class="min-w-0">
        <div class="mb-2 flex flex-wrap gap-1.5">
          <Badge v-if="listing.is_synthetic" tone="warn">Synthetic demo listing</Badge>
          <Badge v-if="listing.price_cut_pct" tone="accent">Price cut {{ pct(listing.price_cut_pct) }} from {{ moneyShort(listing.original_price) }}</Badge>
          <Badge v-if="listing.days_on_market !== null">{{ listing.days_on_market }} days listed</Badge>
        </div>
        <h1 class="text-2xl font-semibold tracking-tight">{{ listing.title }}</h1>
        <p class="mt-1 text-sm text-text-2">{{ [listing.street, listing.community, listing.region, listing.city].filter(Boolean).join(' · ') }}</p>
      </div>
      <div class="text-right">
        <p class="num text-3xl font-medium tracking-tight">{{ money(listing.price) }}</p>
        <Button variant="outline" size="sm" class="mt-3" :disabled="saving" @click="toggleSave()">
          <BookmarkCheck v-if="isSaved" class="h-4 w-4 text-accent" /><Bookmark v-else class="h-4 w-4" />
          {{ isSaved ? 'Saved' : 'Save deal' }}
        </Button>
      </div>
    </header>

    <dl class="mt-6 grid grid-cols-2 gap-x-6 gap-y-3 rounded-2xl border border-border bg-surface p-5 sm:grid-cols-4 lg:grid-cols-8">
      <div v-for="f in facts" :key="f.label">
        <dt class="text-xs text-muted">{{ f.label }}</dt>
        <dd class="num mt-0.5 text-sm">{{ f.value }}</dd>
      </div>
    </dl>

    <div class="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div class="space-y-6">
        <Panel eyebrow="Is the price fair?" title="Asking price vs comparable listings">
          <template v-if="insights?.valuation">
            <FairValue :valuation="insights.valuation" />
            <CompsMap
              v-if="listing.latitude !== null && listing.longitude !== null"
              class="mt-5"
              :subject="{ latitude: listing.latitude, longitude: listing.longitude }"
              :comps="insights.valuation.comps"
            />
          </template>
          <p v-else-if="insights" class="text-sm text-text-2">Not enough comparable listings nearby to estimate a fair value.</p>
          <Skeleton v-else class="h-32" />
        </Panel>

        <Panel eyebrow="Will it cash-flow?" title="Monthly cash flow">
          <CashFlowPanel
            v-if="insights?.cash_flow"
            :initial="insights.cash_flow.inputs"
            :asking-price="listing.price"
            :rent="insights.rent"
            :rate="insights.rate"
            @change="assumptions = $event"
          />
          <p v-else-if="insights" class="text-sm text-text-2">
            No rent benchmark for {{ listing.city }} yet —
            <RouterLink to="/analyze" class="text-accent hover:underline">analyze it with your own rent</RouterLink>.
          </p>
          <Skeleton v-else class="h-64" />
        </Panel>

        <Panel eyebrow="Seller signals" title="Asking price history">
          <PriceHistory v-if="history" :points="history.items" />
        </Panel>
      </div>

      <aside class="space-y-6">
        <Panel v-if="market" eyebrow="Market context" :title="listing.city">
          <dl class="grid grid-cols-2 gap-4">
            <Stat
              label="This $/sq ft vs city"
              :value="listing.price_per_sqft && market.median_price_per_sqft ? signedPct(((listing.price_per_sqft - market.median_price_per_sqft) / market.median_price_per_sqft) * 100, 0) : '—'"
              :sub="`City median $${Math.round(market.median_price_per_sqft ?? 0)}`"
            />
            <Stat
              label="Gross yield"
              :value="pct(listing.gross_yield_pct)"
              :sub="`City median ${pct(market.median_gross_yield_pct)}`"
            />
            <Stat label="Days listed" :value="listing.days_on_market?.toString() ?? '—'" :sub="`City median ${market.median_days_on_market ?? '—'}`" />
            <Stat label="Cap rate" :value="pct(listing.cap_rate_pct, 2)" :sub="`City median ${pct(market.median_cap_rate_pct, 2)}`" />
          </dl>
        </Panel>

        <Panel eyebrow="Neighbourhood" :title="insights?.area?.name ?? listing.community ?? 'Nearby'">
          <NeighbourhoodFacts :area="insights?.area ?? null" :places="places ?? null" />
        </Panel>

        <Panel v-if="insights?.ml" eyebrow="Experimental" title="Model estimate">
          <p class="num text-xl">{{ moneyShort(insights.ml.predicted_price) }}</p>
          <p class="mt-1 text-xs text-text-2">
            {{ Math.round(insights.ml.coverage * 100) }}% of held-out listings fell within
            {{ moneyShort(insights.ml.price_low) }}–{{ moneyShort(insights.ml.price_high) }} ({{ insights.ml.model_version }}).
          </p>
        </Panel>
      </aside>
    </div>
  </article>
</template>
