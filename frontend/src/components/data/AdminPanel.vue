<script setup lang="ts">
/** Operators: data coverage, load history, and jobs on the workers. */
import { useMutation, useQuery, useQueryCache } from '@pinia/colada'
import { ref } from 'vue'
import Badge from '@/components/ui/Badge.vue'
import Button from '@/components/ui/Button.vue'
import { inputClass } from '@/components/ui/inputClass'
import Panel from '@/components/ui/Panel.vue'
import { api } from '@/lib/api'
import { date, num } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { AdminStatus } from '@/lib/types'

const cache = useQueryCache()
const { data: status, refresh } = useQuery({ key: ['admin-status'], query: () => api<AdminStatus>('/admin/status') })

const COVERAGE_LABELS: Record<string, string> = {
  listings: 'Active listings', synthetic_listings: 'Synthetic listings', properties: 'Assessment-roll properties',
  neighbourhood_boundaries: 'Neighbourhood polygons', census_areas: 'Census stats (area rows)', rent_benchmarks: 'Rent benchmarks',
  schools: 'Schools', transit_stops: 'Transit stops', rental_yields: 'Listings with yields',
}
const CITIES = ['Toronto', 'Vancouver', 'Calgary', 'Edmonton', 'Ottawa', 'Montreal']
const NATIONAL = [
  { key: 'bank_of_canada', label: 'Bank of Canada rates' },
  { key: 'statcan_nhpi', label: 'New Housing Price Index' },
  { key: 'census_da_points', label: 'Census area points' },
]
const city = ref('Vancouver')
const message = ref('')

const { mutate: run, isLoading: running } = useMutation({
  mutation: (job: { path: string; body?: unknown; label: string }) =>
    api<{ job_id: string }>(job.path, { method: 'POST', body: job.body }).then((r) => ({ ...r, label: job.label })),
  onSuccess: (r) => (message.value = `Queued: ${r.label} (job ${r.job_id.slice(0, 8)})`),
  onError: (e) => (message.value = `Could not queue: ${e.message}`),
  onSettled: () => setTimeout(() => cache.invalidateQueries({ key: ['admin-status'] }), 1500),
})
</script>

<template>
  <div>
    <div class="flex items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-semibold tracking-tight">Data operations</h1>
        <p class="mt-2 text-sm text-text-2">What is loaded, and the jobs that load it.</p>
      </div>
      <div class="flex items-center gap-2 text-xs">
        <Badge :tone="status?.broker === 'up' ? 'good' : 'bad'">Queue {{ status?.broker ?? '…' }}</Badge>
        <Badge :tone="status?.workers.length ? 'good' : 'warn'">{{ status?.workers.length ?? 0 }} workers</Badge>
        <Button variant="ghost" size="sm" @click="refresh()">Refresh</Button>
      </div>
    </div>

    <p v-if="message" class="mt-4 rounded-lg bg-accent-soft px-3 py-2 text-sm text-accent" role="status">{{ message }}</p>

    <div class="mt-8 grid gap-6 lg:grid-cols-2">
      <Panel title="Coverage">
        <dl class="divide-y divide-border text-sm">
          <div v-for="(value, key) in status?.coverage" :key="key" class="flex justify-between py-2">
            <dt class="text-text-2">{{ COVERAGE_LABELS[key] ?? key }}</dt>
            <dd class="num" :class="value ? '' : 'text-muted'">{{ value === null ? 'not migrated' : num(value) }}</dd>
          </div>
        </dl>
      </Panel>

      <Panel title="Load data">
        <div class="space-y-5">
          <div>
            <p class="mb-2 text-xs text-muted">Demo &amp; reference</p>
            <div class="flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" :disabled="running" @click="run({ path: '/admin/ingest', body: { command: 'rents' }, label: 'rent benchmarks' })">Rent benchmarks</Button>
              <Button variant="secondary" size="sm" :disabled="running" @click="run({ path: '/admin/ingest', body: { command: 'seed' }, label: 'synthetic listings' })">Synthetic listings</Button>
              <Button variant="secondary" size="sm" :disabled="running" @click="run({ path: '/admin/ingest', body: { command: 'osm' }, label: 'OpenStreetMap amenities' })">OSM amenities</Button>
            </div>
          </div>
          <div>
            <p class="mb-2 text-xs text-muted">City open data (boundaries first, then assessments, permits, crime, transit)</p>
            <div class="flex gap-2">
              <select v-model="city" :class="cn(inputClass, 'h-8 w-40 text-xs')" aria-label="City">
                <option v-for="c in CITIES" :key="c">{{ c }}</option>
              </select>
              <Button size="sm" :disabled="running" @click="run({ path: '/admin/ingest', body: { command: 'opendata', cities: [city] }, label: `${city} open data` })">Load {{ city }}</Button>
            </div>
          </div>
          <div>
            <p class="mb-2 text-xs text-muted">National</p>
            <div class="flex flex-wrap gap-2">
              <Button v-for="s in NATIONAL" :key="s.key" variant="secondary" size="sm" :disabled="running" @click="run({ path: '/admin/ingest', body: { command: 'opendata', sources: [s.key] }, label: s.label })">{{ s.label }}</Button>
            </div>
          </div>
          <div>
            <p class="mb-2 text-xs text-muted">Insights</p>
            <div class="flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" :disabled="running" @click="run({ path: '/admin/insights/recompute', label: 'recompute yields' })">Recompute yields</Button>
              <Button variant="secondary" size="sm" :disabled="running" @click="run({ path: '/admin/insights/retrain', label: 'retrain model' })">Retrain model</Button>
            </div>
          </div>
        </div>
      </Panel>
    </div>

    <Panel title="Open-data load history" class="mt-6">
      <table v-if="status?.open_data_loads.length" class="w-full text-sm">
        <thead class="text-left text-xs text-muted">
          <tr><th class="pb-2 font-normal">Source</th><th class="pb-2 font-normal">Status</th><th class="pb-2 text-right font-normal">Rows</th><th class="pb-2 text-right font-normal">When</th></tr>
        </thead>
        <tbody>
          <tr v-for="(l, i) in status.open_data_loads" :key="i" class="border-t border-border align-top">
            <td class="py-2">{{ l.source }}<p v-if="l.message" class="mt-0.5 max-w-xl text-xs text-bad">{{ l.message }}</p></td>
            <td class="py-2"><Badge :tone="l.status === 'ok' ? 'good' : 'bad'">{{ l.status }}</Badge></td>
            <td class="num py-2 text-right">{{ num(l.row_count) }}</td>
            <td class="num py-2 text-right text-text-2">{{ date(l.loaded_at) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="text-sm text-text-2">Nothing loaded from open data yet.</p>
    </Panel>
  </div>
</template>
