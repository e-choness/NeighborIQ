<script setup lang="ts">
/** Asking price over time as a step line (prices change in steps, not slopes). */
import { computed, ref } from 'vue'
import { date, moneyShort } from '@/lib/format'
import type { PricePoint } from '@/lib/types'

const props = defineProps<{ points: PricePoint[] }>()
const W = 560
const H = 140
const PAD = { l: 8, r: 64, t: 12, b: 22 }

const series = computed(() => {
  const pts = props.points.map((p) => ({ t: new Date(p.recorded_at).getTime(), price: p.price }))
  if (!pts.length) return null
  const now = Date.now()
  const t0 = pts[0].t
  const t1 = Math.max(now, pts[pts.length - 1].t + 1)
  const prices = pts.map((p) => p.price)
  const lo = Math.min(...prices)
  const hi = Math.max(...prices)
  const pad = (hi - lo) * 0.25 || hi * 0.02
  const x = (t: number) => PAD.l + ((t - t0) / (t1 - t0)) * (W - PAD.l - PAD.r)
  const y = (p: number) => PAD.t + (1 - (p - (lo - pad)) / (hi + pad - (lo - pad))) * (H - PAD.t - PAD.b)
  let d = `M${x(pts[0].t)},${y(pts[0].price)}`
  for (let i = 1; i < pts.length; i++) d += ` H${x(pts[i].t)} V${y(pts[i].price)}`
  d += ` H${x(t1)}`
  return { pts: pts.map((p) => ({ ...p, cx: x(p.t), cy: y(p.price) })), d, t0, t1, lastY: y(pts[pts.length - 1].price) }
})
const active = ref<number | null>(null)
</script>

<template>
  <p v-if="points.length <= 1" class="text-sm text-text-2">
    No price changes since it was listed{{ points[0] ? ` on ${date(points[0].recorded_at)}` : '' }}.
  </p>
  <div v-else-if="series" class="relative">
    <svg :viewBox="`0 0 ${W} ${H}`" class="w-full" role="img" :aria-label="`Asking price changed ${points.length - 1} times, from ${moneyShort(points[0].price)} to ${moneyShort(points[points.length - 1].price)}`">
      <line :x1="PAD.l" :x2="W - PAD.r" :y1="H - PAD.b" :y2="H - PAD.b" stroke="var(--border-strong)" />
      <path :d="series.d" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round" />
      <g v-for="(p, i) in series.pts" :key="i">
        <circle :cx="p.cx" :cy="p.cy" r="4" fill="var(--surface)" stroke="var(--accent)" stroke-width="2" />
        <circle :cx="p.cx" :cy="p.cy" r="14" fill="transparent" @mouseenter="active = i" @mouseleave="active = null" @focus="active = i" tabindex="0" />
      </g>
      <text :x="W - PAD.r + 8" :y="series.lastY + 4" class="num" font-size="11" fill="var(--text)">{{ moneyShort(points[points.length - 1].price) }}</text>
      <text :x="PAD.l" :y="H - 6" font-size="10" fill="var(--muted)">{{ date(points[0].recorded_at) }}</text>
      <text :x="W - PAD.r" :y="H - 6" font-size="10" fill="var(--muted)" text-anchor="end">Today</text>
    </svg>
    <div
      v-if="active !== null"
      class="glass pointer-events-none absolute rounded-md px-2 py-1 text-xs"
      :style="{ left: `${(series.pts[active].cx / W) * 100}%`, top: `${(series.pts[active].cy / H) * 100 - 30}%` }"
    >
      <span class="num">{{ moneyShort(points[active].price) }}</span> · {{ date(points[active].recorded_at) }}
    </div>
  </div>
</template>
