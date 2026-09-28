<script setup lang="ts">
/**
 * Deal analyzer for any property — including ones that are not listed here.
 * Location comes from an assessment-roll address lookup (when that open data is
 * loaded) or from picking a neighbourhood; the rest is a few numbers. The result
 * stays pinned in the sheet; every assumption opens in a dialog (desktop) or the
 * full-height sheet (phones). The map flies to the place and shows nearby comps.
 */
import { MapPin, SlidersHorizontal, X } from '@lucide/vue'
import { useQuery } from '@pinia/colada'
import { refDebounced } from '@vueuse/core'
import { DialogClose, DialogContent, DialogDescription, DialogOverlay, DialogPortal, DialogRoot, DialogTitle } from 'reka-ui'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import CashFlowPanel from '@/components/analysis/CashFlowPanel.vue'
import Sheet from '@/components/shell/Sheet.vue'
import Button from '@/components/ui/Button.vue'
import Field from '@/components/ui/Field.vue'
import { inputClass } from '@/components/ui/inputClass'
import { api } from '@/lib/api'
import { money, moneyShort, num, pct, PROPERTY_TYPE_LABEL, signedMoney } from '@/lib/format'
import type { CashFlowInput, CashFlowResult, PropertyRecord, RateContext, RentEstimate, Valuation } from '@/lib/types'
import { isPhone } from '@/lib/viewport'
import { useCity } from '@/stores/city'
import { useMapStage } from '@/stores/mapStage'
import { useShell } from '@/stores/shell'

const cities = useCity()
const stage = useMapStage()
const shell = useShell()

const deal = reactive({
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
const neighbourhood = ref<number | null>(null)
const address = ref('')

// A new city (top bar) means a new place
watch(() => cities.city, () => {
  Object.assign(deal, { latitude: null, longitude: null, place: '' })
  neighbourhood.value = null
  address.value = ''
})

// Location: neighbourhood picker
const { data: communities } = useQuery({
  key: () => ['communities', cities.city],
  query: () => api<{ items: { id: number; name: string; latitude: number | null; longitude: number | null }[] }>('/communities', { query: { city: cities.city } }),
  enabled: () => Boolean(cities.city),
})
watch(neighbourhood, (id) => {
  const c = communities.value?.items.find((x) => x.id === id)
  if (c?.latitude != null && c.longitude != null) {
    Object.assign(deal, { latitude: c.latitude, longitude: c.longitude, place: c.name })
  }
})

// Location: assessment-roll address lookup (only when open data is loaded)
const addressQuery = refDebounced(address, 250)
const { data: matches } = useQuery({
  key: () => ['property-lookup', cities.city, addressQuery.value],
  query: () => api<{ items: PropertyRecord[] }>('/properties/lookup', { query: { q: addressQuery.value, city: cities.city } }),
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
  city: cities.city, price: deal.price, sqft: deal.sqft, rooms: deal.rooms,
  property_type: deal.property_type, latitude: deal.latitude, longitude: deal.longitude,
})), 300)
const { data: valuation } = useQuery({
  key: () => ['adhoc-valuation', valuationKey.value],
  query: () => api<Valuation | null>('/valuation', { method: 'POST', body: JSON.parse(valuationKey.value) }),
  enabled: () => ready.value,
})
const { data: rent } = useQuery({
  key: () => ['rent', cities.city, deal.rooms],
  query: () => api<RentEstimate | null>('/rents', { query: { city: cities.city, bedrooms: deal.rooms } }),
  enabled: () => Boolean(cities.city),
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
    city: cities.city,
    monthly_rent: rent.value?.monthly_rent ?? 0,
    property_tax_annual: deal.property_tax || Math.round(deal.price * 0.007),
    condo_fee_monthly: deal.property_type === 'condo' ? deal.condo_fee : 0,
    insurance_monthly: deal.property_type === 'condo' ? 35 : 125,
    maintenance_pct: deal.property_type === 'condo' ? 5 : 8,
  }
})
// The pinned result uses the adjusted assumptions once the viewer has touched them
const adjusted = ref<CashFlowInput | null>(null)
watch(initialCashFlow, () => (adjusted.value = null))
const inputs = computed(() => adjusted.value ?? initialCashFlow.value)
const cashKey = refDebounced(computed(() => (inputs.value ? JSON.stringify(inputs.value) : '')), 250)
const { data: cash } = useQuery({
  key: () => ['cashflow', cashKey.value],
  query: () => api<CashFlowResult>('/cashflow', { method: 'POST', body: JSON.parse(cashKey.value) }),
  enabled: () => Boolean(cashKey.value),
  placeholderData: (previous: CashFlowResult | undefined) => previous,
  staleTime: 5 * 60_000,
})

const valueLine = computed(() => {
  if (!ready.value) return 'Choose an address or neighbourhood to compare with nearby listings.'
  const v = valuation.value
  const type = PROPERTY_TYPE_LABEL[deal.property_type]?.toLowerCase() ?? 'property'
  if (v === undefined) return 'Comparing with nearby listings…'
  if (v === null) return `Not enough comparable ${type} listings near ${deal.place}.`
  if (v.verdict === 'in_line') return `In line with comparable ${type}s in ${deal.place} (fair value ${moneyShort(v.fair_value)})`
  return `${pct(Math.abs(v.delta_pct))} ${v.verdict === 'below' ? 'below' : 'above'} comparable ${type}s in ${deal.place} (fair value ${moneyShort(v.fair_value)})`
})

// Map: fly to the place with its comps; the city's hex view until a place is chosen
onMounted(() => stage.show('home'))
watch(
  [() => deal.latitude, () => deal.longitude, valuation],
  ([lat, lon, v]) => {
    if (lat === null || lon === null) {
      stage.show('home')
      return
    }
    stage.mode = 'listing'
    stage.zoom = 13.8
    stage.subject = { latitude: lat, longitude: lon }
    stage.comps = (v?.comps ?? []).map((c) => ({ id: c.house_id, latitude: c.latitude, longitude: c.longitude }))
  },
)

// "Adjust all assumptions": a dialog on desktop, the full-height sheet on phones
const dialogOpen = ref(false)
const expanded = ref(false)
function adjustAll() {
  if (isPhone.value) {
    expanded.value = !expanded.value
    if (expanded.value) shell.snap = 'full'
  } else {
    dialogOpen.value = true
  }
}
</script>

<template>
  <Sheet side="left" label="Analyze a property" body-class="p-5">
    <p class="eyebrow">Analyze a property</p>
    <h1 class="font-display mt-2 text-[30px] leading-[1.08] tracking-[0.02em]">Would this property pay for itself?</h1>
    <p class="mt-2 text-[13px] leading-[1.55] text-text-2">
      Enter a property you found anywhere. You get its price against comparable listings nearby and a monthly cash
      flow you can adjust.
    </p>

    <div class="mt-4 space-y-3">
      <Field label="Street address" for="a-address" hint="Matches the city's public assessment roll, where published.">
        <div class="relative">
          <input id="a-address" v-model="address" :class="inputClass" placeholder="e.g. 120 King St" autocomplete="off" />
          <ul
            v-if="matches?.items.length && address !== picked?.address"
            class="absolute inset-x-0 top-11 z-20 max-h-60 overflow-y-auto rounded-xl border border-border bg-bg p-1 shadow-[var(--shadow)]"
          >
            <li v-for="m in matches.items" :key="m.id">
              <button type="button" class="w-full rounded-lg px-2.5 py-2 text-left text-[13px] hover:bg-surface-2" @click="pick(m)">
                {{ m.address }}
                <span class="block text-[11px] text-muted">
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
    </div>

    <p v-if="deal.place" class="mt-2.5 flex items-center gap-1.5 text-xs text-accent"><MapPin class="h-3.5 w-3.5" /> {{ deal.place }}</p>

    <div class="mt-3.5 grid grid-cols-2 gap-3 border-t border-border pt-3.5">
      <Field label="Asking price ($)" for="a-price"><input id="a-price" v-model.number="deal.price" type="number" step="1000" :class="[inputClass, 'num']" /></Field>
      <Field label="Size (sq ft)" for="a-sqft"><input id="a-sqft" v-model.number="deal.sqft" type="number" step="10" :class="[inputClass, 'num']" /></Field>
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
      <Field v-if="deal.property_type === 'condo'" label="Condo fee ($/mo)" for="a-fee"><input id="a-fee" v-model.number="deal.condo_fee" type="number" step="10" :class="[inputClass, 'num']" /></Field>
      <Field label="Property tax ($/yr)" for="a-tax" :hint="deal.property_tax ? undefined : 'Blank: ~0.7% of price'">
        <input id="a-tax" v-model.number="deal.property_tax" type="number" step="50" :class="[inputClass, 'num']" placeholder="Estimate" />
      </Field>
    </div>

    <!-- Result, pinned in the sheet -->
    <section aria-label="Result" class="mt-[18px] rounded-2xl border border-border bg-surface-2 p-4" aria-live="polite">
      <p class="eyebrow">Result</p>
      <p class="mt-2 text-sm text-text-2">{{ valueLine }}</p>
      <template v-if="cash">
        <p class="num mt-1.5 text-[28px] font-medium" :class="cash.monthly_cash_flow < 0 ? 'text-bad' : 'text-good'">
          {{ signedMoney(cash.monthly_cash_flow) }} <span class="font-sans text-xs font-normal text-muted">/ month</span>
        </p>
        <dl class="mt-3 grid grid-cols-2 gap-3">
          <div><dt class="text-[11px] text-muted">Cap rate</dt><dd class="num mt-[3px] text-[15px] font-medium">{{ pct(cash.cap_rate_pct, 2) }}</dd></div>
          <div><dt class="text-[11px] text-muted">Cash-on-cash</dt><dd class="num mt-[3px] text-[15px] font-medium">{{ pct(cash.cash_on_cash_pct) }}</dd></div>
          <div><dt class="text-[11px] text-muted">Debt coverage</dt><dd class="num mt-[3px] text-[15px] font-medium">{{ cash.dscr === null ? '—' : `${num(cash.dscr, 2)}×` }}</dd></div>
          <div><dt class="text-[11px] text-muted">Cash to close</dt><dd class="num mt-[3px] text-[15px] font-medium">{{ moneyShort(cash.cash_invested) }}</dd></div>
        </dl>
        <p class="mt-3 text-[11px] text-muted">
          Rent {{ money(inputs?.monthly_rent) }}/mo{{ rent ? ' from the city benchmark' : '' }} ·
          {{ inputs?.down_payment_pct }}% down · {{ inputs?.interest_rate_pct }}% · {{ inputs?.amortization_years }} yr
        </p>
      </template>
      <p v-else-if="rent === null" class="mt-2 text-xs text-muted">No rent benchmark for {{ cities.city }} — set the rent under “Adjust all assumptions”.</p>
      <Button v-if="initialCashFlow" variant="secondary" size="sm" class="mt-3" :aria-expanded="isPhone ? expanded : undefined" @click="adjustAll">
        <SlidersHorizontal class="h-3.5 w-3.5" /> {{ isPhone && expanded ? 'Hide assumptions' : 'Adjust all assumptions' }}
      </Button>
    </section>

    <div v-if="isPhone && expanded && initialCashFlow" class="mt-5">
      <CashFlowPanel :initial="adjusted ?? initialCashFlow" :asking-price="deal.price" :rent="rent" :rate="defaults?.rate" @change="adjusted = $event" />
    </div>
  </Sheet>

  <DialogRoot v-model:open="dialogOpen">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-40 bg-[var(--scrim)]" />
      <DialogContent class="glass fixed left-1/2 top-1/2 z-50 flex max-h-[calc(100dvh-48px)] w-[min(640px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-[22px] text-text outline-none">
        <div class="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div>
            <DialogTitle class="font-display text-[26px] tracking-[0.02em]">Cash flow assumptions</DialogTitle>
            <DialogDescription class="mt-1 text-xs text-text-2">{{ deal.place || cities.city }} · asking {{ money(deal.price) }}</DialogDescription>
          </div>
          <DialogClose aria-label="Close" class="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-border bg-surface-2 text-text-2 hover:text-text">
            <X class="h-3.5 w-3.5" />
          </DialogClose>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto p-5">
          <CashFlowPanel v-if="initialCashFlow" :initial="adjusted ?? initialCashFlow" :asking-price="deal.price" :rent="rent" :rate="defaults?.rate" @change="adjusted = $event" />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
