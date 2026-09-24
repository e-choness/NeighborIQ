<script setup lang="ts">
/**
 * Deal analyzer for any property — including ones that are not listed here.
 * Location comes from an assessment-roll address lookup (when that open data is
 * loaded) or from picking a neighbourhood; the rest is a few numbers.
 */
import { MapPin } from '@lucide/vue'
import { useQuery } from '@pinia/colada'
import { refDebounced } from '@vueuse/core'
import { computed, reactive, ref, watch } from 'vue'
import CashFlowPanel from '@/components/analysis/CashFlowPanel.vue'
import FairValue from '@/components/analysis/FairValue.vue'
import Field from '@/components/ui/Field.vue'
import { inputClass } from '@/components/ui/inputClass'
import Panel from '@/components/ui/Panel.vue'
import { api } from '@/lib/api'
import { money, PROPERTY_TYPE_LABEL } from '@/lib/format'
import type { CashFlowInput, Market, PropertyRecord, RateContext, RentEstimate, Valuation } from '@/lib/types'

const { data: markets } = useQuery({ key: ['markets'], query: () => api<Market[]>('/markets') })

const deal = reactive({
  city: '',
  price: 650000,
  sqft: 800,
  rooms: 2,
  property_type: 'condo',
  condo_fee: 550,
  property_tax: null as number | null,
  latitude: null as number | null,
  longitude: null as number | null,
  place: '',
})
watch(markets, (m) => {
  if (!deal.city && m?.length) deal.city = m[0].city
}, { immediate: true })

// Location: neighbourhood picker
const { data: communities } = useQuery({
  key: () => ['communities', deal.city],
  query: () => api<{ items: { id: number; name: string; latitude: number | null; longitude: number | null }[] }>('/communities', { query: { city: deal.city } }),
  enabled: () => Boolean(deal.city),
})
const neighbourhood = ref<number | null>(null)
watch(neighbourhood, (id) => {
  const c = communities.value?.items.find((x) => x.id === id)
  if (c?.latitude != null && c.longitude != null) {
    Object.assign(deal, { latitude: c.latitude, longitude: c.longitude, place: c.name })
  }
})

// Location: assessment-roll address lookup (only when open data is loaded)
const address = ref('')
const addressQuery = refDebounced(address, 250)
const { data: matches } = useQuery({
  key: () => ['property-lookup', deal.city, addressQuery.value],
  query: () => api<{ items: PropertyRecord[] }>('/properties/lookup', { query: { q: addressQuery.value, city: deal.city } }),
  enabled: () => addressQuery.value.trim().length >= 3,
})
const picked = ref<PropertyRecord | null>(null)
function pick(p: PropertyRecord) {
  picked.value = p
  address.value = p.address
  Object.assign(deal, {
    latitude: p.latitude ?? deal.latitude,
    longitude: p.longitude ?? deal.longitude,
    place: p.address,
    property_tax: p.tax_levy ?? deal.property_tax,
    sqft: p.floor_area_sqft ?? deal.sqft,
  })
}

// Analysis
const ready = computed(() => deal.latitude !== null && deal.longitude !== null && deal.price > 0 && deal.sqft > 0)
const valuationKey = refDebounced(computed(() => JSON.stringify({
  city: deal.city, price: deal.price, sqft: deal.sqft, rooms: deal.rooms,
  property_type: deal.property_type, latitude: deal.latitude, longitude: deal.longitude,
})), 300)
const { data: valuation } = useQuery({
  key: () => ['adhoc-valuation', valuationKey.value],
  query: () => api<Valuation | null>('/valuation', { method: 'POST', body: JSON.parse(valuationKey.value) }),
  enabled: () => ready.value,
})
const { data: rent } = useQuery({
  key: () => ['rent', deal.city, deal.rooms],
  query: () => api<RentEstimate | null>('/rents', { query: { city: deal.city, bedrooms: deal.rooms } }),
  enabled: () => Boolean(deal.city),
})
const { data: defaults } = useQuery({
  key: ['cashflow-defaults'],
  query: () => api<{ inputs: Omit<CashFlowInput, 'price' | 'monthly_rent' | 'city'>; rate: RateContext | null }>('/cashflow/defaults'),
})

const initialCashFlow = computed<CashFlowInput | null>(() => {
  if (!defaults.value) return null
  const d = defaults.value.inputs
  return {
    ...d,
    price: deal.price,
    city: deal.city,
    monthly_rent: rent.value?.monthly_rent ?? 0,
    property_tax_annual: deal.property_tax || Math.round(deal.price * 0.007),
    condo_fee_monthly: deal.property_type === 'condo' ? deal.condo_fee : 0,
    insurance_monthly: deal.property_type === 'condo' ? 35 : 125,
    maintenance_pct: deal.property_type === 'condo' ? 5 : 8,
  }
})
</script>

<template>
  <div>
    <header class="max-w-2xl">
      <p class="eyebrow mb-2">Analyze a property</p>
      <h1 class="text-3xl font-semibold tracking-tight">Would this property pay for itself?</h1>
      <p class="mt-2 text-sm leading-relaxed text-text-2">
        Enter a property you found anywhere. You get its price against comparable listings nearby and a
        monthly cash flow you can adjust — rent, rate, down payment, costs.
      </p>
    </header>

    <div class="mt-8 grid gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
      <Panel title="The property" class="self-start lg:sticky lg:top-20">
        <div class="space-y-4">
          <Field label="City" for="a-city">
            <select id="a-city" v-model="deal.city" :class="inputClass" @change="Object.assign(deal, { latitude: null, longitude: null, place: '' }); neighbourhood = null">
              <option v-for="m in markets" :key="m.city" :value="m.city">{{ m.city }}</option>
            </select>
          </Field>

          <Field label="Street address" for="a-address" hint="Matches the city's public assessment roll, where published.">
            <div class="relative">
              <input id="a-address" v-model="address" :class="inputClass" placeholder="e.g. 1200 Main St" autocomplete="off" />
              <ul v-if="matches?.items.length && address !== picked?.address" class="absolute z-20 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-border bg-surface shadow-xl">
                <li v-for="m in matches.items" :key="m.id">
                  <button class="w-full px-3 py-2 text-left text-sm hover:bg-surface-2" @click="pick(m)">
                    {{ m.address }}
                    <span class="block text-xs text-muted">
                      {{ [m.area_name, m.year_built && `built ${m.year_built}`, m.assessed_value && `assessed ${money(m.assessed_value)}`].filter(Boolean).join(' · ') }}
                    </span>
                  </button>
                </li>
              </ul>
            </div>
          </Field>

          <Field label="Or pick the neighbourhood" for="a-hood">
            <select id="a-hood" v-model.number="neighbourhood" :class="inputClass">
              <option :value="null">Choose…</option>
              <option v-for="c in communities?.items" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </Field>

          <p v-if="deal.place" class="flex items-center gap-1.5 text-xs text-accent"><MapPin class="h-3.5 w-3.5" /> {{ deal.place }}</p>

          <div class="grid grid-cols-2 gap-3 border-t border-border pt-4">
            <Field label="Asking price ($)" for="a-price"><input id="a-price" v-model.number="deal.price" type="number" step="1000" :class="inputClass" /></Field>
            <Field label="Size (sq ft)" for="a-sqft"><input id="a-sqft" v-model.number="deal.sqft" type="number" step="10" :class="inputClass" /></Field>
            <Field label="Bedrooms" for="a-beds">
              <select id="a-beds" v-model.number="deal.rooms" :class="inputClass">
                <option v-for="n in [0, 1, 2, 3, 4, 5]" :key="n" :value="n">{{ n === 0 ? 'Studio' : n }}</option>
              </select>
            </Field>
            <Field label="Type" for="a-type">
              <select id="a-type" v-model="deal.property_type" :class="inputClass">
                <option v-for="(label, t) in PROPERTY_TYPE_LABEL" :key="t" :value="t">{{ label }}</option>
              </select>
            </Field>
            <Field v-if="deal.property_type === 'condo'" label="Condo fee ($/mo)" for="a-fee"><input id="a-fee" v-model.number="deal.condo_fee" type="number" step="10" :class="inputClass" /></Field>
            <Field label="Property tax ($/yr)" for="a-tax" :hint="deal.property_tax ? undefined : 'Blank: ~0.7% of price'">
              <input id="a-tax" v-model.number="deal.property_tax" type="number" step="50" :class="inputClass" placeholder="Estimate" />
            </Field>
          </div>
        </div>
      </Panel>

      <div class="space-y-6">
        <Panel eyebrow="Is the price fair?" title="Against comparable listings">
          <FairValue v-if="valuation" :valuation="valuation" />
          <p v-else-if="!ready" class="text-sm text-text-2">Choose an address or neighbourhood to compare with nearby listings.</p>
          <p v-else-if="valuation === null" class="text-sm text-text-2">Not enough comparable {{ PROPERTY_TYPE_LABEL[deal.property_type]?.toLowerCase() }} listings near {{ deal.place }}.</p>
        </Panel>
        <Panel eyebrow="Will it cash-flow?" title="Monthly cash flow">
          <CashFlowPanel
            v-if="initialCashFlow"
            :initial="initialCashFlow"
            :asking-price="deal.price"
            :rent="rent"
            :rate="defaults?.rate"
          />
        </Panel>
      </div>
    </div>
  </div>
</template>
