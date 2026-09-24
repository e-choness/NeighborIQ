<script setup lang="ts">
/** Saved deals, each recomputed with the assumptions it was saved with, compared side by side. */
import { Trash2 } from '@lucide/vue'
import { useMutation, useQuery, useQueryCache } from '@pinia/colada'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import Button from '@/components/ui/Button.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import { api } from '@/lib/api'
import { moneyShort, pct, signedMoney } from '@/lib/format'
import type { CashFlowInput, CashFlowResult, Insights, SavedDeal } from '@/lib/types'

const cache = useQueryCache()
const { data: deals, isLoading } = useQuery({ key: ['portfolio'], query: () => api<SavedDeal[]>('/portfolio/saved') })

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

const { mutate: remove } = useMutation({
  mutation: (houseId: number) => api(`/portfolio/saved/${houseId}`, { method: 'DELETE' }),
  onSettled: () => cache.invalidateQueries({ key: ['portfolio'] }),
})
</script>

<template>
  <div>
    <h1 class="text-3xl font-semibold tracking-tight">Portfolio</h1>
    <p class="mt-2 text-sm text-text-2">Saved deals, recalculated with the assumptions you saved them with.</p>

    <Skeleton v-if="isLoading" class="mt-8 h-40" />
    <div v-else-if="!deals?.length" class="mt-10 rounded-2xl border border-dashed border-border p-10 text-center">
      <p class="font-medium">No saved deals yet</p>
      <p class="mt-1 text-sm text-text-2">Open a listing and choose “Save deal” to keep its analysis here.</p>
      <Button to="/explore" variant="secondary" class="mt-4">Browse listings</Button>
    </div>

    <div v-else class="mt-8 overflow-x-auto rounded-2xl border border-border bg-surface">
      <table class="w-full min-w-[52rem] text-sm">
        <thead class="text-left text-xs text-muted">
          <tr class="border-b border-border">
            <th class="px-4 py-3 font-normal">Property</th>
            <th class="px-4 py-3 text-right font-normal">Price</th>
            <th class="px-4 py-3 text-right font-normal">vs comps</th>
            <th class="px-4 py-3 text-right font-normal">Cash flow / mo</th>
            <th class="px-4 py-3 text-right font-normal">Cap rate</th>
            <th class="px-4 py-3 text-right font-normal">Cash-on-cash</th>
            <th class="px-4 py-3 text-right font-normal">Cash to close</th>
            <th class="px-4 py-3"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in deals" :key="d.id" class="border-b border-border last:border-0">
            <td class="px-4 py-3">
              <RouterLink :to="`/listings/${d.house_id}`" class="font-medium hover:text-accent">{{ d.house.title }}</RouterLink>
              <p class="text-xs text-muted">{{ d.house.community }}, {{ d.house.city }}<template v-if="d.notes"> · {{ d.notes }}</template></p>
            </td>
            <td class="num px-4 py-3 text-right">{{ moneyShort(d.assumptions?.price ?? d.house.price) }}</td>
            <td class="num px-4 py-3 text-right">
              <template v-if="results?.[d.house_id]?.valuation">{{ results[d.house_id].valuation!.delta_pct > 0 ? '+' : '' }}{{ pct(results[d.house_id].valuation!.delta_pct) }}</template>
              <template v-else>—</template>
            </td>
            <td class="num px-4 py-3 text-right" :class="(results?.[d.house_id]?.cf?.monthly_cash_flow ?? 0) >= 0 ? 'text-good' : 'text-bad'">
              {{ results?.[d.house_id]?.cf ? signedMoney(results[d.house_id].cf!.monthly_cash_flow) : '…' }}
            </td>
            <td class="num px-4 py-3 text-right">{{ pct(results?.[d.house_id]?.cf?.cap_rate_pct, 2) }}</td>
            <td class="num px-4 py-3 text-right">{{ pct(results?.[d.house_id]?.cf?.cash_on_cash_pct) }}</td>
            <td class="num px-4 py-3 text-right">{{ moneyShort(results?.[d.house_id]?.cf?.cash_invested) }}</td>
            <td class="px-2 py-3 text-right">
              <Button variant="danger" size="icon" :aria-label="`Remove ${d.house.title}`" @click="remove(d.house_id)"><Trash2 class="h-4 w-4" /></Button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
