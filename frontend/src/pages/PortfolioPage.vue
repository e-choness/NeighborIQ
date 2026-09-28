<script setup lang="ts">
/** Saved deals, each recomputed with the assumptions it was saved with, compared side by side. */
import { Trash2 } from '@lucide/vue'
import { useMutation, useQuery, useQueryCache } from '@pinia/colada'
import { computed, onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import Sheet from '@/components/shell/Sheet.vue'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'
import { moneyShort, pct, signedMoney } from '@/lib/format'
import type { CashFlowInput, CashFlowResult, Insights, SavedDeal } from '@/lib/types'
import { isPhone } from '@/lib/viewport'
import { useMapStage } from '@/stores/mapStage'
import { useShell } from '@/stores/shell'

const cache = useQueryCache()
const stage = useMapStage()
const shell = useShell()
const { data: deals, isLoading } = useQuery({ key: ['portfolio'], query: () => api<SavedDeal[]>('/portfolio/saved') })

onMounted(() => stage.show('overview'))
watch(() => deals.value, (d) => (stage.listings = (d ?? []).map((x) => x.house)), { immediate: true })

// One insights + cash-flow computation per saved deal
const ids = computed(() => (deals.value ?? []).map((d) => d.house_id).join(','))
const { data: results } = useQuery({
  key: () => ['portfolio-results', ids.value],
  enabled: () => Boolean(deals.value?.length),
  query: async () => {
    const out: Record<number, { cf: CashFlowResult | null; valuation: Insights['valuation'] }> = {}
    await Promise.all((deals.value ?? []).map(async (d) => {
      const insights = await api<Insights>(`/houses/${d.house_id}/insights`)
      const inputs: CashFlowInput | null = insights.cash_flow ? { ...insights.cash_flow.inputs, ...(d.assumptions ?? {}) } : null
      out[d.house_id] = {
        valuation: insights.valuation,
        cf: inputs ? await api<CashFlowResult>('/cashflow', { method: 'POST', body: inputs }) : null,
      }
    }))
    return out
  },
})

const rows = computed(() =>
  (deals.value ?? []).map((d) => {
    const r = results.value?.[d.house_id]
    const delta = r?.valuation?.delta_pct
    return {
      id: d.house_id,
      title: d.house.title,
      sub: `${d.house.community ?? ''}${d.house.community ? ', ' : ''}${d.house.city}${d.notes ? ` · ${d.notes}` : ''}`,
      price: moneyShort(d.assumptions?.price ?? d.house.price),
      delta: delta === undefined || delta === null ? '—' : `${delta > 0 ? '+' : ''}${pct(delta)}`,
      cf: r?.cf ? signedMoney(r.cf.monthly_cash_flow) : r ? '—' : '…',
      negative: (r?.cf?.monthly_cash_flow ?? 0) < 0,
      cap: pct(r?.cf?.cap_rate_pct, 2),
      coc: pct(r?.cf?.cash_on_cash_pct),
      invested: moneyShort(r?.cf?.cash_invested),
    }
  }),
)

const { mutate: remove } = useMutation({
  mutation: (houseId: number) => api(`/portfolio/saved/${houseId}`, { method: 'DELETE' }),
  onSuccess: () => shell.flash('Removed from portfolio'),
  onSettled: () => cache.invalidateQueries({ key: ['portfolio'] }),
})
const GRID = 'grid grid-cols-[minmax(0,2.4fr)_repeat(6,minmax(0,1fr))_44px] items-center gap-3 px-4'
</script>

<template>
  <Sheet side="center" label="Portfolio" :body-class="isPhone ? 'p-4' : 'p-6'">
    <div class="mx-auto max-w-[1040px]">
      <h1 class="font-display text-[36px] tracking-[0.03em]">Portfolio</h1>
      <p class="mt-1.5 text-sm text-text-2">Saved deals, recalculated with the assumptions you saved them with.</p>

      <Skeleton v-if="isLoading" class="mt-6 h-40" />
      <div v-else-if="!deals?.length" class="mt-6 rounded-[18px] border border-dashed border-border p-10 text-center">
        <p class="font-medium">No saved deals yet</p>
        <p class="mt-1.5 text-sm text-text-2">Open a listing and choose “Save deal” to keep its analysis here.</p>
        <Button to="/explore" variant="secondary" class="mt-4">Browse listings</Button>
      </div>

      <div v-else-if="!isPhone" class="mt-[22px] overflow-hidden rounded-[18px] border border-border" role="table" aria-label="Saved deals">
        <div :class="[GRID, 'border-b border-border py-3 text-xs text-muted']" role="row">
          <span role="columnheader">Property</span>
          <span role="columnheader" class="text-right">Price</span>
          <span role="columnheader" class="text-right">vs comps</span>
          <span role="columnheader" class="text-right">Cash flow / mo</span>
          <span role="columnheader" class="text-right">Cap rate</span>
          <span role="columnheader" class="text-right">Cash-on-cash</span>
          <span role="columnheader" class="text-right">Cash to close</span>
          <span role="columnheader"><span class="sr-only">Actions</span></span>
        </div>
        <div v-for="d in rows" :key="d.id" :class="[GRID, 'border-b border-border py-3 text-sm last:border-0']" role="row" data-testid="portfolio-row">
          <span class="min-w-0" role="cell">
            <RouterLink :to="`/listings/${d.id}`" class="block truncate font-medium text-text hover:text-accent">{{ d.title }}</RouterLink>
            <span class="block truncate text-xs text-muted">{{ d.sub }}</span>
          </span>
          <span role="cell" class="num text-right">{{ d.price }}</span>
          <span role="cell" class="num text-right">{{ d.delta }}</span>
          <span role="cell" class="num text-right" :class="d.negative ? 'text-bad' : 'text-good'">{{ d.cf }}</span>
          <span role="cell" class="num text-right">{{ d.cap }}</span>
          <span role="cell" class="num text-right">{{ d.coc }}</span>
          <span role="cell" class="num text-right">{{ d.invested }}</span>
          <span role="cell">
            <button type="button" :aria-label="`Remove ${d.title}`" class="grid h-8 w-8 place-items-center rounded-[10px] text-bad hover:bg-bad/10" @click="remove(d.id)">
              <Trash2 class="h-4 w-4" />
            </button>
          </span>
        </div>
      </div>

      <div v-else class="mt-[18px] flex flex-col gap-2.5">
        <div v-for="d in rows" :key="d.id" class="rounded-2xl border border-border bg-surface-2 p-3.5" data-testid="portfolio-row">
          <div class="flex justify-between gap-2.5">
            <RouterLink :to="`/listings/${d.id}`" class="min-w-0 truncate font-medium text-text">{{ d.title }}</RouterLink>
            <button type="button" :aria-label="`Remove ${d.title}`" class="shrink-0 text-bad" @click="remove(d.id)"><Trash2 class="h-4 w-4" /></button>
          </div>
          <div class="truncate text-xs text-muted">{{ d.sub }}</div>
          <div class="num mt-2.5 grid grid-cols-3 gap-2 text-[13px]">
            <span>{{ d.price }}</span>
            <span :class="d.negative ? 'text-bad' : 'text-good'">{{ d.cf }}</span>
            <span class="text-right">{{ d.cap }} cap</span>
          </div>
        </div>
      </div>
    </div>
  </Sheet>
</template>
