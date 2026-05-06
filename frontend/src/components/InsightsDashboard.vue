<template>
  <div class="space-y-4">
    <!-- AI Insights header -->
    <div class="flex items-center gap-2">
      <div class="w-6 h-6 rounded-md bg-cyan-500/20 flex items-center justify-center">
        <svg class="w-3.5 h-3.5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      </div>
      <h3 class="text-sm font-semibold text-white">AI Insights</h3>
      <span class="ml-auto text-xs text-slate-500">Updated 6h ago</span>
    </div>

    <!-- Metric cards grid -->
    <div class="grid grid-cols-2 gap-3">
      <MetricCard
        label="Predicted Price"
        :value="formatPrice(insights?.predicted_price)"
        :sub="insights?.confidence ? `${(insights.confidence * 100).toFixed(0)}% confidence` : ''"
        color="violet"
        icon="chart-bar"
      />
      <MetricCard
        label="Gross Yield"
        :value="insights?.gross_yield ? `${(insights.gross_yield * 100).toFixed(1)}%` : 'N/A'"
        :sub="insights?.net_yield ? `Net: ${(insights.net_yield * 100).toFixed(1)}%` : ''"
        color="emerald"
        icon="trending-up"
      />
    </div>

    <!-- Price range bar -->
    <div v-if="insights?.price_low && insights?.price_high && insights?.predicted_price" class="bg-slate-700/40 rounded-lg p-3">
      <div class="flex justify-between text-xs text-slate-400 mb-2">
        <span>{{ formatPrice(insights.price_low) }}</span>
        <span class="text-violet-400 font-semibold">{{ formatPrice(insights.predicted_price) }}</span>
        <span>{{ formatPrice(insights.price_high) }}</span>
      </div>
      <div class="h-2 bg-slate-600/50 rounded-full relative overflow-hidden">
        <div
          class="absolute left-0 top-0 h-full bg-gradient-to-r from-emerald-500/60 to-violet-500/60 rounded-full"
          :style="{ width: rangePercent + '%' }"
        ></div>
        <div
          class="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-violet-400 rounded-full border-2 border-white shadow-lg"
          :style="{ left: `calc(${rangePercent}% - 6px)` }"
        ></div>
      </div>
      <p class="text-xs text-slate-500 mt-1.5">80% prediction confidence interval</p>
    </div>

    <!-- Annual rent estimate -->
    <div v-if="insights?.annual_rent" class="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
      <div class="flex items-center gap-2">
        <svg class="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div>
          <p class="text-xs text-emerald-400 font-medium">Est. Annual Rent</p>
          <p class="text-sm text-white font-semibold">{{ formatPrice(insights.annual_rent) }}</p>
        </div>
      </div>
    </div>

    <!-- No data fallback -->
    <div v-if="!insights" class="bg-slate-700/30 rounded-lg p-4 text-center">
      <svg class="w-8 h-8 text-slate-600 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
      <p class="text-xs text-slate-500">AI insights not yet available</p>
      <p class="text-xs text-slate-600 mt-0.5">Predictions run every 6 hours</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MetricCard from './MetricCard.vue'
import type { HouseInsights } from '@/types'

const props = defineProps<{
  insights: HouseInsights | null
}>()

function formatPrice(price: number | null | undefined): string {
  if (!price) return 'N/A'
  if (price >= 1_000_000) return `$${(price / 1_000_000).toFixed(2)}M`
  if (price >= 1_000) return `$${(price / 1_000).toFixed(0)}K`
  return `$${price}`
}

const rangePercent = computed(() => {
  if (!props.insights?.price_low || !props.insights?.price_high || !props.insights?.predicted_price) return 50
  const { price_low, price_high, predicted_price } = props.insights
  return Math.round(((predicted_price - price_low) / (price_high - price_low)) * 100)
})
</script>
