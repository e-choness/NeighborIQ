<script setup lang="ts">
/** Open-data context for a listing's neighbourhood, and its nearest amenities. */
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { distance, money, num, pct } from '@/lib/format'
import type { AreaContext, Neighbourhood } from '@/lib/types'

const props = defineProps<{ area: AreaContext | null; places: Neighbourhood | null }>()

const FACTS: { key: string; label: string; fmt: (v: number) => string }[] = [
  { key: 'median_household_income', label: 'Median household income', fmt: (v) => money(v) },
  { key: 'renter_share_pct', label: 'Households renting', fmt: (v) => pct(v, 0) },
  { key: 'median_rent_paid', label: 'Median rent paid', fmt: (v) => money(v) },
  { key: 'transit_departures_per_km2', label: 'Weekday transit departures / km²', fmt: (v) => num(v) },
  { key: 'crime_per_1000', label: 'Major crime per 1,000 residents', fmt: (v) => num(v, 1) },
  { key: 'permit_units_24m', label: 'New units permitted (24 mo)', fmt: (v) => num(v) },
]
const facts = computed(() =>
  FACTS.flatMap((f) => {
    const stat = props.area?.stats[f.key]
    return stat && stat.value !== null ? [{ ...f, value: f.fmt(stat.value), period: stat.period }] : []
  }),
)
const groups = computed(() =>
  props.places
    ? [
        { label: 'Transit', items: props.places.transit },
        { label: 'Schools', items: props.places.schools },
        { label: 'Hospital', items: props.places.hospitals },
      ].filter((g) => g.items.length)
    : [],
)
</script>

<template>
  <div class="space-y-5">
    <div v-if="facts.length">
      <p class="mb-2 text-xs text-muted">{{ area?.name }}</p>
      <dl class="divide-y divide-border">
        <div v-for="f in facts" :key="f.key" class="flex items-baseline justify-between gap-4 py-2 text-sm">
          <dt class="text-text-2">{{ f.label }}<span v-if="f.period" class="ml-1 text-[11px] text-muted">{{ f.period }}</span></dt>
          <dd class="num">{{ f.value }}</dd>
        </div>
      </dl>
    </div>

    <div v-for="g in groups" :key="g.label">
      <p class="mb-1.5 text-xs text-muted">{{ g.label }}</p>
      <ul class="space-y-1.5 text-sm">
        <li v-for="p in g.items" :key="p.name" class="flex items-baseline justify-between gap-3">
          <span class="truncate">{{ p.name }}<span v-if="p.detail && g.label === 'Transit'" class="ml-1.5 text-xs text-muted">{{ p.detail }}</span></span>
          <span class="num shrink-0 text-xs text-text-2">{{ distance(p.distance_m) }}</span>
        </li>
      </ul>
    </div>

    <p v-if="!facts.length && !groups.length" class="text-sm text-text-2">
      No neighbourhood data loaded for this city yet. Census, transit, crime and amenities come from public
      open data — <RouterLink to="/data" class="text-accent hover:underline">see sources</RouterLink>.
    </p>
    <p v-if="groups.length" class="text-[11px] text-muted">{{ places?.attribution }}</p>
  </div>
</template>
