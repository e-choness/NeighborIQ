<script setup lang="ts">
/**
 * Asking price against comparable listings. The range bar spans the comps'
 * interquartile $/sq ft × size; markers show the fair value and the asking price.
 * Direction is carried by words and an icon as well as colour.
 */
import { ArrowDownRight, ArrowUpRight, Equal } from '@lucide/vue'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import Badge from '@/components/ui/Badge.vue'
import InfoTip from '@/components/ui/InfoTip.vue'
import { distance, moneyShort, pct } from '@/lib/format'
import { theme } from '@/lib/theme'
import type { Valuation } from '@/lib/types'
import { DIVERGING } from '@/theme/palette'

const props = defineProps<{ valuation: Valuation }>()
const v = computed(() => props.valuation)

const verdictText = computed(() => {
  const d = Math.abs(v.value.delta_pct).toFixed(1)
  if (v.value.verdict === 'below') return `${d}% below comparable listings`
  if (v.value.verdict === 'above') return `${d}% above comparable listings`
  return 'In line with comparable listings'
})
const color = computed(() => {
  const c = DIVERGING[theme.value]
  return v.value.verdict === 'below' ? c.below : v.value.verdict === 'above' ? c.above : c.neutral
})

// Scale: pad the band so both markers always fit
const scale = computed(() => {
  const values = [v.value.fair_value_low, v.value.fair_value_high, v.value.asking_price, v.value.fair_value]
  const lo = Math.min(...values)
  const hi = Math.max(...values)
  const pad = (hi - lo) * 0.15 || hi * 0.05
  return { lo: lo - pad, hi: hi + pad }
})
const at = (x: number) => `${((x - scale.value.lo) / (scale.value.hi - scale.value.lo)) * 100}%`
const confidenceTone = { high: 'good', medium: 'neutral', low: 'warn' } as const
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center gap-2">
      <component :is="v.verdict === 'below' ? ArrowDownRight : v.verdict === 'above' ? ArrowUpRight : Equal" class="h-5 w-5" :style="{ color }" aria-hidden="true" />
      <p class="text-lg font-semibold tracking-tight">{{ verdictText }}</p>
    </div>
    <p class="mt-1 text-sm text-text-2">
      Fair value <span class="num text-text">{{ moneyShort(v.fair_value) }}</span>
      from {{ v.comps.length }} similar listings within {{ distance(v.radius_m) }}
      at a median <span class="num text-text">${{ Math.round(v.median_price_per_sqft) }}</span>/sq ft
      (this one: <span class="num">${{ Math.round(v.subject_price_per_sqft) }}</span>).
    </p>

    <!-- Range bar -->
    <div class="relative mt-6 h-12" role="img" :aria-label="`Asking ${moneyShort(v.asking_price)}; comparable range ${moneyShort(v.fair_value_low)} to ${moneyShort(v.fair_value_high)}; fair value ${moneyShort(v.fair_value)}`">
      <div class="absolute inset-x-0 top-5 h-1.5 rounded-full bg-surface-2" />
      <div class="absolute top-5 h-1.5 rounded-full bg-border-strong" :style="{ left: at(v.fair_value_low), width: `calc(${at(v.fair_value_high)} - ${at(v.fair_value_low)})` }" />
      <div class="absolute top-3.5 h-4 w-0.5 -translate-x-1/2 rounded bg-text-2" :style="{ left: at(v.fair_value) }" />
      <div class="absolute top-2.5 h-6 w-1 -translate-x-1/2 rounded" :style="{ left: at(v.asking_price), background: color }" />
      <span class="num absolute top-9 -translate-x-1/2 whitespace-nowrap text-[11px] text-muted" :style="{ left: at(v.fair_value_low) }">{{ moneyShort(v.fair_value_low) }}</span>
      <span class="num absolute top-9 -translate-x-1/2 whitespace-nowrap text-[11px] text-muted" :style="{ left: at(v.fair_value_high) }">{{ moneyShort(v.fair_value_high) }}</span>
      <span class="num absolute -top-3 -translate-x-1/2 whitespace-nowrap text-[11px] font-medium text-text" :style="{ left: at(v.asking_price) }">Asking {{ moneyShort(v.asking_price) }}</span>
    </div>

    <div class="mt-4 flex flex-wrap items-center gap-2 text-xs text-muted">
      <Badge :tone="confidenceTone[v.confidence]">{{ v.confidence }} confidence</Badge>
      <span>Compared with {{ v.basis }}, not sold prices</span>
      <InfoTip text="Comparables share the city and property type, are within ±1 bedroom and ±35% of the size, and are the nearest active listings. Confidence reflects how many were found and how tightly their $/sq ft agree. Asking prices run above sale prices in slow markets." />
    </div>

    <details class="group mt-4">
      <summary class="cursor-pointer list-none text-xs text-text-2 hover:text-text">
        <span class="group-open:hidden">Show the {{ v.comps.length }} comparables</span>
        <span class="hidden group-open:inline">Hide comparables</span>
      </summary>
      <table class="mt-3 w-full text-xs">
        <thead class="text-left text-muted">
          <tr>
            <th class="py-1.5 font-normal">Listing</th>
            <th class="py-1.5 text-right font-normal">Distance</th>
            <th class="py-1.5 text-right font-normal">Price</th>
            <th class="py-1.5 text-right font-normal">$/sq ft</th>
            <th class="py-1.5 text-right font-normal">vs median</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in v.comps" :key="c.house_id" class="border-t border-border">
            <td class="max-w-56 truncate py-2"><RouterLink :to="`/listings/${c.house_id}`" class="hover:text-accent">{{ c.title }}</RouterLink></td>
            <td class="num py-2 text-right text-text-2">{{ distance(c.distance_m) }}</td>
            <td class="num py-2 text-right">{{ moneyShort(c.price) }}</td>
            <td class="num py-2 text-right">${{ Math.round(c.price_per_sqft) }}</td>
            <td class="num py-2 text-right text-text-2">{{ pct(((c.price_per_sqft - v.median_price_per_sqft) / v.median_price_per_sqft) * 100) }}</td>
          </tr>
        </tbody>
      </table>
    </details>
  </div>
</template>
