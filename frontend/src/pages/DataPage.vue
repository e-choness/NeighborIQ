<script setup lang="ts">
/** Sources & methodology for everyone; data operations (the Admin tab) for admins. */
import { useQuery } from '@pinia/colada'
import { computed, defineAsyncComponent, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sheet from '@/components/shell/Sheet.vue'
import Panel from '@/components/ui/Panel.vue'
import Segmented from '@/components/ui/Segmented.vue'
import { api } from '@/lib/api'
import { date, pct } from '@/lib/format'
import type { DataSource, Indicator, Market } from '@/lib/types'
import { isPhone } from '@/lib/viewport'
import { useAuth } from '@/stores/auth'
import { useMapStage } from '@/stores/mapStage'

const AdminPanel = defineAsyncComponent(() => import('@/components/data/AdminPanel.vue'))
const auth = useAuth()
const route = useRoute()
const router = useRouter()
const stage = useMapStage()
onMounted(() => stage.show('overview'))

type Tab = 'sources' | 'admin'
const tab = computed<Tab>({
  get: () => (route.query.tab === 'admin' && auth.isAdmin ? 'admin' : 'sources'),
  set: (t) => router.replace({ query: { ...route.query, tab: t === 'admin' ? 'admin' : undefined } }),
})
const tabs = [{ value: 'sources' as const, label: 'Sources' }, { value: 'admin' as const, label: 'Admin' }]
const { data: sources } = useQuery({ key: ['data-sources'], query: () => api<{ items: DataSource[] }>('/data-sources') })
const { data: markets } = useQuery({ key: ['markets'], query: () => api<Market[]>('/markets') })
const { data: indicators } = useQuery({ key: ['indicators'], query: () => api<{ items: Indicator[] }>('/indicators') })

const METHODS = [
  {
    title: 'Fair value',
    body: 'The median asking $/sq ft of the nearest active listings of the same city and property type, within ±1 bedroom and ±35% of the size, times this property’s size. The range is the comparables’ interquartile spread. Confidence depends on how many comparables were found and how closely they agree.',
    limit: 'Uses asking prices, not sold prices — Canadian sold data is licensed by real estate boards. In a slow market, asking prices overstate what homes sell for.',
  },
  {
    title: 'Rent',
    body: 'A city-wide average for the bedroom count, in the format of CMHC’s Rental Market Survey.',
    limit: 'Averages include long-standing tenancies, so the asking rent for a vacant unit is usually higher. The shipped table holds placeholder values until the official CMHC figures are loaded.',
  },
  {
    title: 'Cash flow',
    body: 'Rent less vacancy, property tax, condo fee, insurance, maintenance and management, less the mortgage payment. Canadian fixed-rate mortgages compound semi-annually; under 20% down adds a CMHC insurance premium; closing costs include the provincial (and Toronto municipal) land transfer tax.',
    limit: 'Every input is an assumption you can change. It is a projection, not financial advice, and ignores income tax, appreciation and capital expenditures beyond the reserve.',
  },
  {
    title: 'Yields and cap rate',
    body: 'Gross yield = annual rent ÷ price. Cap rate = net operating income (after operating costs, before the mortgage) ÷ price.',
    limit: 'Both use the rent benchmark above, so they inherit its limits.',
  },
  {
    title: 'Neighbourhood facts',
    body: 'Census 2021 values are aggregated from dissemination areas whose representative point falls inside the neighbourhood; medians are population-weighted means of the area medians. Transit intensity counts scheduled weekday departures. Crime is reported incidents per 1,000 residents.',
    limit: 'Aggregated medians are approximations. Crime data covers reported incidents only and is not available for every city.',
  },
]
</script>

<template>
  <Sheet side="center" label="Sources and methodology" :body-class="isPhone ? 'p-4' : 'p-6'">
    <div class="mx-auto max-w-[1040px]">
      <div class="flex flex-wrap items-end justify-between gap-3.5">
        <div>
          <h1 class="font-display text-[36px] tracking-[0.03em]">{{ tab === 'admin' ? 'Data operations' : 'Sources & methodology' }}</h1>
          <p class="mt-1.5 text-sm text-text-2">
            {{ tab === 'admin' ? 'What is loaded, and the jobs that load it.' : 'What each number means, where it comes from, and where it can mislead you.' }}
          </p>
        </div>
        <Segmented v-if="auth.isAdmin" v-model="tab" :options="tabs" label="Data view" />
      </div>

      <div v-if="tab === 'admin'" class="mt-3.5"><AdminPanel /></div>

      <template v-else>
        <div class="mt-[22px] grid items-start gap-4 [grid-template-columns:repeat(auto-fit,minmax(300px,1fr))]">
          <div class="flex flex-col gap-4">
            <Panel title="What is real in this deployment">
              <ul class="space-y-2 text-sm">
                <li v-for="m in markets" :key="m.city" class="flex justify-between gap-4">
                  <span>{{ m.city }} listings</span>
                  <span :class="m.synthetic_share_pct > 0 ? 'text-warn' : 'text-good'">
                    {{ m.synthetic_share_pct >= 100 ? 'Synthetic demo data' : m.synthetic_share_pct > 0 ? `${pct(m.synthetic_share_pct, 0)} synthetic` : 'Real' }}
                  </span>
                </li>
              </ul>
              <p class="mt-3.5 text-xs leading-[1.55] text-muted">
                Synthetic listings are generated for demonstration: neighbourhood names and locations are real, prices and
                sizes are not. Real listings require a licensed source such as CREA’s Data Distribution Facility through a
                brokerage — NeighborIQ does not scrape MLS® or REALTOR.ca.
              </p>
              <p class="mt-3 text-xs text-muted">Maps © OpenStreetMap contributors (ODbL) · OpenFreeMap.</p>
            </Panel>

            <Panel v-if="indicators?.items.length" title="Rates in use">
              <ul class="space-y-2 text-sm">
                <li v-for="i in indicators.items" :key="i.series" class="flex justify-between gap-4">
                  <span class="text-text-2">{{ i.label }}</span>
                  <span class="num">{{ i.latest }}{{ i.unit === 'percent' ? '%' : '' }} <span class="text-xs text-muted">{{ date(i.date) }}</span></span>
                </li>
              </ul>
            </Panel>

            <Panel title="Loaded public data">
              <table v-if="sources?.items.length" class="w-full text-sm">
                <thead class="text-left text-xs text-muted">
                  <tr><th class="pb-2 font-normal">Source</th><th class="pb-2 font-normal">Licence</th><th class="pb-2 text-right font-normal">Updated</th></tr>
                </thead>
                <tbody>
                  <tr v-for="s in sources.items" :key="s.source" class="border-t border-border">
                    <td class="py-2">{{ s.attribution || s.source }}</td>
                    <td class="py-2 text-text-2">{{ s.licence }}</td>
                    <td class="num py-2 text-right text-text-2">{{ date(s.loaded_at) }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-else class="text-sm text-text-2">
                No public data sets loaded yet. Operators load boundaries, assessment rolls, census, transit, crime and rates
                with <code class="num text-xs">python -m ingestion opendata</code> (see docs/guide/data-sources.md).
              </p>
            </Panel>
          </div>

          <div class="flex flex-col gap-4">
            <div v-for="m in METHODS" :key="m.title" class="border-l-2 border-border pl-3.5">
              <h2 class="font-medium">{{ m.title }}</h2>
              <p class="mt-1 text-[13px] leading-[1.55] text-text-2">{{ m.body }}</p>
              <p class="mt-[5px] text-[13px] leading-[1.55] text-muted"><span class="text-warn">Limit:</span> {{ m.limit }}</p>
            </div>
          </div>
        </div>

        <p class="mt-6 border-t border-border pt-4 text-xs leading-relaxed text-muted">
          Estimates from asking prices and public data — not appraisals or advice.
          <template v-if="sources?.items.length">
            Data: {{ [...new Set(sources.items.map((s) => s.attribution).filter(Boolean))].join(' · ') }}.
          </template>
        </p>
      </template>
    </div>
  </Sheet>
</template>
