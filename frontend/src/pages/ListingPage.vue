<script setup lang="ts">
/**
 * One listing in a right-hand sheet, with the map showing it and its comparables the whole
 * time. Short header, then four tabs (?tab= keeps them shareable): Value · Cash flow · History · Area.
 */
import { ArrowLeft, Bookmark, BookmarkCheck, X } from '@lucide/vue'
import { useMutation, useQuery, useQueryCache } from '@pinia/colada'
import { TabsContent, TabsIndicator, TabsList, TabsRoot, TabsTrigger } from 'reka-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import CashFlowPanel from '@/components/analysis/CashFlowPanel.vue'
import FairValue from '@/components/analysis/FairValue.vue'
import NeighbourhoodFacts from '@/components/analysis/NeighbourhoodFacts.vue'
import PriceHistory from '@/components/analysis/PriceHistory.vue'
import Sheet from '@/components/shell/Sheet.vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api, ApiError } from '@/lib/api'
import { theme } from '@/lib/theme'
import { beds, distance, money, moneyShort, pct, PROPERTY_TYPE_LABEL, signedPct } from '@/lib/format'
import type { CashFlowInput, Insights, Listing, Market, Neighbourhood, PricePoint, SavedDeal } from '@/lib/types'
import { useAuth } from '@/stores/auth'
import { useMapStage } from '@/stores/mapStage'
import { useShell } from '@/stores/shell'
import { MARKERS } from '@/theme/palette'

const props = defineProps<{ id: number }>()
const auth = useAuth()
const route = useRoute()
const router = useRouter()
const cache = useQueryCache()
const stage = useMapStage()
const shell = useShell()

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

// Map: the subject and its comparables, at street level
onMounted(() => stage.show('listing'))
watch(
  [listing, () => insights.value?.valuation],
  ([l, v]) => {
    stage.mode = 'listing'
    stage.zoom = 14.2
    stage.subject = l?.latitude != null && l.longitude != null ? { latitude: l.latitude, longitude: l.longitude } : null
    stage.comps = (v?.comps ?? []).map((c) => ({ id: c.house_id, latitude: c.latitude, longitude: c.longitude }))
  },
  { immediate: true },
)

// Tabs, kept in the URL
const TABS = [
  { value: 'value', label: 'Value' },
  { value: 'cash', label: 'Cash flow' },
  { value: 'history', label: 'History' },
  { value: 'area', label: 'Area' },
] as const
type Tab = (typeof TABS)[number]['value']
const tab = computed<Tab>({
  get: () => (TABS.some((t) => t.value === route.query.tab) ? (route.query.tab as Tab) : 'value'),
  set: (t) => router.replace({ query: { ...route.query, tab: t === 'value' ? undefined : t } }),
})

// Back / close: Explore with the filters it had
const back = computed(() => {
  const q = shell.exploreQuery
  const sameCity = !q.city || q.city === listing.value?.city
  return { path: '/explore', query: sameCity && Object.keys(q).length ? q : { city: listing.value?.city } }
})

// Saving
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
      return null
    }
    if (isSaved.value) {
      await api(`/portfolio/saved/${props.id}`, { method: 'DELETE' })
      return 'Removed from portfolio'
    }
    await api('/portfolio/save', { method: 'POST', body: { house_id: props.id, assumptions: assumptions.value } })
    return 'Saved to portfolio with your assumptions'
  },
  onSuccess: (message) => message && shell.flash(message),
  onError: (e) => shell.flash(`Could not save: ${e.message}`),
  onSettled: () => cache.invalidateQueries({ key: ['portfolio'] }),
})

const notFound = computed(() => error.value instanceof ApiError && error.value.status === 404)
const photo = computed(() => listing.value?.images?.[0] ?? null)
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
const marketStats = computed(() => {
  const l = listing.value
  const m = market.value
  if (!l || !m) return []
  return [
    {
      label: 'This $/sq ft vs city',
      value: l.price_per_sqft && m.median_price_per_sqft ? signedPct(((l.price_per_sqft - m.median_price_per_sqft) / m.median_price_per_sqft) * 100, 0) : '—',
      sub: `City median ${money(m.median_price_per_sqft)}`,
    },
    { label: 'Gross yield', value: pct(l.gross_yield_pct), sub: `City median ${pct(m.median_gross_yield_pct)}` },
    { label: 'Days listed', value: l.days_on_market?.toString() ?? '—', sub: `City median ${m.median_days_on_market ?? '—'}` },
    { label: 'Cap rate', value: pct(l.cap_rate_pct, 2), sub: `City median ${pct(m.median_cap_rate_pct, 2)}` },
  ]
})
</script>

<template>
  <Sheet side="right" :label="listing?.title ?? 'Listing'">
    <template #header>
      <div class="flex shrink-0 items-center justify-between pl-[18px] pr-3.5 pt-3">
        <RouterLink :to="back" class="inline-flex items-center gap-1.5 py-1.5 text-xs text-text-2 hover:text-text">
          <ArrowLeft class="h-3.5 w-3.5" /> {{ listing?.city ?? '' }} listings
        </RouterLink>
        <RouterLink :to="back" aria-label="Close" title="Close" class="grid h-8 w-8 place-items-center rounded-full border border-border bg-surface-2 text-text-2 hover:text-text">
          <X class="h-3.5 w-3.5" />
        </RouterLink>
      </div>
    </template>

    <div v-if="notFound" class="px-[18px] py-16 text-center">
      <p class="text-lg font-medium">This listing is no longer available.</p>
      <Button :to="back" variant="secondary" class="mt-4">Browse listings</Button>
    </div>

    <div v-else-if="!listing" class="space-y-4 p-[18px]">
      <Skeleton class="h-8 w-2/3" />
      <Skeleton class="h-40" />
    </div>

    <article v-else>
      <div class="px-[18px] pt-2.5">
        <div class="flex flex-wrap gap-1.5">
          <Badge v-if="listing.is_synthetic" tone="warn">Synthetic demo listing</Badge>
          <Badge v-if="listing.price_cut_pct" tone="accent">Price cut {{ pct(listing.price_cut_pct) }} from {{ moneyShort(listing.original_price) }}</Badge>
          <Badge v-if="listing.days_on_market !== null">{{ listing.days_on_market }} days listed</Badge>
        </div>
        <div class="mt-3 flex items-start justify-between gap-3.5">
          <div class="min-w-0">
            <h1 class="font-display text-[30px] leading-[1.08] tracking-[0.02em] [text-wrap:balance]">{{ listing.title }}</h1>
            <p class="mt-1.5 text-[13px] text-text-2">{{ [listing.street, listing.community, listing.region, listing.city].filter(Boolean).join(' · ') }}</p>
          </div>
          <div class="shrink-0 text-right">
            <p class="num text-2xl font-medium tracking-[-0.02em]">{{ money(listing.price) }}</p>
            <button
              type="button"
              class="mt-2 inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-[10px] border px-3 text-xs disabled:opacity-50"
              :class="isSaved ? 'border-transparent bg-accent-deep text-accent-ink' : 'border-border bg-surface-2 text-text'"
              :disabled="saving"
              @click="toggleSave()"
            >
              <BookmarkCheck v-if="isSaved" class="h-[15px] w-[15px]" /><Bookmark v-else class="h-[15px] w-[15px]" />
              {{ isSaved ? 'Saved' : 'Save deal' }}
            </button>
          </div>
        </div>

        <img v-if="photo" :src="photo" alt="Listing photo" class="mt-3.5 h-[190px] w-full rounded-2xl object-cover" />
        <div
          v-else
          class="mt-3.5 grid h-[190px] place-items-center rounded-2xl border border-border bg-[repeating-linear-gradient(135deg,var(--surface-2)_0_10px,transparent_10px_20px)]"
          aria-hidden="true"
        >
          <span class="num text-[11px] uppercase tracking-[0.12em] text-muted">Listing photo</span>
        </div>

        <dl class="mt-3.5 grid grid-cols-4 gap-x-2.5 gap-y-3 rounded-2xl border border-border bg-surface-2 p-3.5">
          <div v-for="f in facts" :key="f.label" class="min-w-0">
            <dt class="text-[11px] text-muted">{{ f.label }}</dt>
            <dd class="num mt-[3px] truncate text-[13px]">{{ f.value }}</dd>
          </div>
        </dl>
      </div>

      <TabsRoot v-model="tab" :unmount-on-hide="false">
        <div class="sticky top-0 z-[2] mt-3.5 border-y border-border bg-panel px-[18px] py-2.5 backdrop-blur-[22px]">
          <TabsList aria-label="Listing sections" class="relative grid grid-cols-4 rounded-xl border border-border bg-surface-2 p-[3px]">
            <TabsIndicator class="absolute bottom-[3px] left-0 top-[3px] w-[var(--reka-tabs-indicator-size)] translate-x-[var(--reka-tabs-indicator-position)] rounded-[9px] bg-seg-on shadow-[inset_0_1px_0_var(--glass-hi),0_1px_3px_rgb(0_0_0/0.2)] transition-transform duration-200 motion-reduce:transition-none" />
            <TabsTrigger
              v-for="t in TABS"
              :key="t.value"
              :value="t.value"
              class="relative z-[1] whitespace-nowrap rounded-[9px] px-1 py-[7px] text-xs font-medium text-text-2 hover:text-text data-[state=active]:text-text"
            >
              {{ t.label }}
            </TabsTrigger>
          </TabsList>
        </div>

        <div class="p-[18px]">
          <TabsContent value="value" class="outline-none">
            <p class="eyebrow">Is the price fair?</p>
            <template v-if="insights?.valuation">
              <div class="mt-2.5"><FairValue :valuation="insights.valuation" /></div>
              <div class="mt-[18px] flex justify-between text-xs text-muted">
                <span>Comparables · shown on the map</span>
                <span class="inline-flex items-center gap-3">
                  <span class="inline-flex items-center gap-1.5"><span class="h-2 w-2 rounded-full" :style="{ background: MARKERS[theme].subject }" />This listing</span>
                  <span class="inline-flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-accent" />Comp</span>
                </span>
              </div>
              <ul class="mt-2 overflow-hidden rounded-[14px] border border-border">
                <li
                  v-for="(c, i) in insights.valuation.comps"
                  :key="c.house_id"
                  class="text-xs transition-colors"
                  :class="[i ? 'border-t border-border' : '', stage.highlightComp === c.house_id ? 'bg-seg-on' : '']"
                  @mouseenter="stage.highlightComp = c.house_id"
                  @mouseleave="stage.highlightComp = null"
                >
                  <RouterLink
                    :to="`/listings/${c.house_id}`"
                    class="grid grid-cols-[minmax(0,1fr)_auto_56px_52px] gap-2.5 px-3 py-[9px] text-text hover:no-underline focus-visible:bg-seg-on"
                    @focus="stage.highlightComp = c.house_id"
                    @blur="stage.highlightComp = null"
                  >
                    <span class="truncate">{{ c.title }}</span>
                    <span class="text-muted">{{ beds(c.rooms) }} · {{ c.sqft.toLocaleString('en-CA') }} sq ft</span>
                    <span class="num text-right">${{ Math.round(c.price_per_sqft) }}</span>
                    <span class="num text-right text-muted">{{ distance(c.distance_m) }}</span>
                  </RouterLink>
                </li>
              </ul>
            </template>
            <p v-else-if="insights" class="mt-2.5 text-sm text-text-2">Not enough comparable listings nearby to estimate a fair value.</p>
            <Skeleton v-else class="mt-2.5 h-32" />

            <div v-if="insights?.ml" class="mt-4 rounded-2xl border border-border bg-surface-2 p-3.5">
              <p class="eyebrow">Experimental · model estimate</p>
              <p class="num mt-1.5 text-xl">{{ moneyShort(insights.ml.predicted_price) }}</p>
              <p class="mt-1 text-xs text-text-2">
                {{ Math.round(insights.ml.coverage * 100) }}% of held-out listings fell within
                {{ moneyShort(insights.ml.price_low) }}–{{ moneyShort(insights.ml.price_high) }} ({{ insights.ml.model_version }}).
              </p>
            </div>
          </TabsContent>

          <TabsContent value="cash" class="outline-none">
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
            <p class="mt-3 text-[11px] leading-normal text-muted">Estimates from asking prices and public data — not appraisals or advice.</p>
          </TabsContent>

          <TabsContent value="history" class="outline-none">
            <p class="eyebrow">Seller signals</p>
            <p class="mt-1.5 text-base font-medium">Asking price history</p>
            <div class="mt-3"><PriceHistory v-if="history" :points="history.items" /></div>
          </TabsContent>

          <TabsContent value="area" class="outline-none">
            <p class="eyebrow">Market context</p>
            <p class="mt-1.5 text-base font-medium">{{ listing.city }}</p>
            <dl v-if="marketStats.length" class="mt-3 grid grid-cols-2 gap-4">
              <div v-for="m in marketStats" :key="m.label">
                <dt class="text-xs text-muted">{{ m.label }}</dt>
                <dd class="num mt-1 text-lg font-medium">{{ m.value }}</dd>
                <p class="mt-0.5 text-xs text-text-2">{{ m.sub }}</p>
              </div>
            </dl>
            <div class="mt-[22px] border-t border-border pt-[18px]">
              <p class="eyebrow">Neighbourhood</p>
              <p class="mt-1.5 text-base font-medium">{{ insights?.area?.name ?? listing.community ?? 'Nearby' }}</p>
              <div class="mt-2"><NeighbourhoodFacts :area="insights?.area ?? null" :places="places ?? null" /></div>
            </div>
          </TabsContent>
        </div>
      </TabsRoot>
    </article>
  </Sheet>
</template>
