<script setup lang="ts">
/**
 * Asking price against comparable listings. The range bar spans the comps'
 * interquartile $/sq ft × size; markers show the fair value and the asking price.
 * Direction is carried by words and an icon as well as colour. The comps themselves
 * are listed by the page, next to the map that shows them.
 */
import { Equal, TrendingDown, TrendingUp } from '@lucide/vue'
import { computed } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import InfoTip from '@/components/ui/InfoTip.vue'
import { distance, moneyShort } from '@/lib/format'
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
    <div class="flex items-center gap-2 text-lg font-medium text-text">
      <component
        :is="v.verdict === 'below' ? TrendingDown : v.verdict === 'above' ? TrendingUp : Equal"
        class="h-[18px] w-[18px]"
        :style="{ color }"
        aria-hidden="true"
      />
      {{ verdictText }}
    </div>
    <p class="mt-1.5 text-[13px] leading-[1.55] text-text-2">
      Fair value <b class="num font-medium text-text">{{ moneyShort(v.fair_value) }}</b>
      from {{ v.comps.length }} similar listings within {{ distance(v.radius_m) }}
      at a median <b class="num font-medium text-text">${{ Math.round(v.median_price_per_sqft) }}</b>/sq ft
      (this one: <span class="num">${{ Math.round(v.subject_price_per_sqft) }}</span>).
    </p>

    <!-- Range bar -->
    <div
      class="relative mt-[30px] h-1.5 rounded-[9px] bg-surface-2"
      role="img"
      :aria-label="`Asking ${moneyShort(v.asking_price)}; comparable range ${moneyShort(v.fair_value_low)} to ${moneyShort(v.fair_value_high)}; fair value ${moneyShort(v.fair_value)}`"
    >
      <div class="absolute inset-y-0 rounded-[9px] bg-bar" :style="{ left: at(v.fair_value_low), width: `calc(${at(v.fair_value_high)} - ${at(v.fair_value_low)})` }" />
      <div class="absolute -top-[5px] h-4 w-0.5 bg-text-2" :style="{ left: at(v.fair_value) }" />
      <div class="absolute -top-1.5 -ml-0.5 h-[18px] w-1 rounded-[3px]" :style="{ left: at(v.asking_price), background: color }">
        <span class="num absolute bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap text-[11px] font-medium text-text">Asking {{ moneyShort(v.asking_price) }}</span>
      </div>
    </div>
    <div class="num mt-2 flex justify-between text-[11px] text-muted">
      <span>Comps range</span><span>{{ moneyShort(v.fair_value_low) }} – {{ moneyShort(v.fair_value_high) }}</span>
    </div>

    <div class="mt-3.5 flex flex-wrap items-center gap-2 text-xs text-muted">
      <Badge :tone="confidenceTone[v.confidence]">{{ v.confidence }} confidence</Badge>
      <span>Compared with {{ v.basis }}, not sold prices</span>
      <InfoTip text="Comparables share the city and property type, are within ±1 bedroom and ±35% of the size, and are the nearest active listings. Confidence reflects how many were found and how tightly their $/sq ft agree. Asking prices run above sale prices in slow markets." />
    </div>
  </div>
</template>
