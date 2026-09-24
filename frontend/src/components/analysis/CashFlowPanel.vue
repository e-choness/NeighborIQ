<script setup lang="ts">
/**
 * Editable rental cash flow. Every assumption is visible and adjustable; results
 * come from the API (POST /cashflow) so the Canadian mortgage maths lives in one
 * place. Inputs are debounced; the last result stays on screen while recomputing.
 */
import { AlertTriangle, TrendingDown, TrendingUp } from '@lucide/vue'
import { useQuery } from '@pinia/colada'
import { refDebounced } from '@vueuse/core'
import { computed, reactive, watch } from 'vue'
import InfoTip from '@/components/ui/InfoTip.vue'
import SliderField from '@/components/ui/SliderField.vue'
import Stat from '@/components/ui/Stat.vue'
import { api } from '@/lib/api'
import { money, moneyShort, num, pct, signedMoney } from '@/lib/format'
import type { CashFlowInput, CashFlowResult, RateContext, RentEstimate } from '@/lib/types'

const props = defineProps<{
  initial: CashFlowInput
  askingPrice?: number
  rent?: RentEstimate | null
  rate?: RateContext | null
}>()
const emit = defineEmits<{ change: [CashFlowInput] }>()

const inputs = reactive<CashFlowInput>({ ...props.initial })
watch(() => props.initial, (next) => Object.assign(inputs, next))
watch(inputs, () => emit('change', { ...inputs }), { deep: true })

const snapshot = computed(() => JSON.stringify(inputs))
const debounced = refDebounced(snapshot, 250)

const { data: result, isLoading } = useQuery({
  key: () => ['cashflow', debounced.value],
  query: () => api<CashFlowResult>('/cashflow', { method: 'POST', body: JSON.parse(debounced.value) }),
  placeholderData: (previous: CashFlowResult | undefined) => previous,
  staleTime: 5 * 60_000,
})

const positive = computed(() => (result.value?.monthly_cash_flow ?? 0) >= 0)
const priceBase = computed(() => props.askingPrice ?? props.initial.price)

/** Where one month of rent goes — the monthly picture an investor actually lives with. */
const flows = computed(() => {
  const r = result.value
  if (!r) return []
  const vacancy = r.gross_monthly_income - r.effective_monthly_income
  const rows = [
    { label: 'Mortgage payment', value: r.monthly_mortgage_payment },
    { label: 'Property tax', value: r.monthly_expenses.property_tax },
    { label: 'Condo fee', value: r.monthly_expenses.condo_fee },
    { label: 'Insurance', value: r.monthly_expenses.insurance },
    { label: 'Maintenance reserve', value: r.monthly_expenses.maintenance },
    { label: 'Management', value: r.monthly_expenses.management },
    { label: 'Vacancy allowance', value: vacancy },
  ].filter((row) => row.value > 0.5)
  const scale = Math.max(r.gross_monthly_income, rows.reduce((s, x) => s + x.value, 0))
  return rows.map((row) => ({ ...row, width: `${(row.value / scale) * 100}%` }))
})
const incomeWidth = computed(() => {
  const r = result.value
  if (!r) return '0%'
  const out = flows.value.reduce((s, x) => s + x.value, 0)
  return `${(r.gross_monthly_income / Math.max(r.gross_monthly_income, out)) * 100}%`
})
</script>

<template>
  <div>
    <div v-if="result" class="flex flex-wrap items-end justify-between gap-4" :class="{ 'opacity-70 transition-opacity': isLoading }">
      <div>
        <p class="text-xs text-muted">Monthly cash flow after mortgage</p>
        <p class="num mt-1 flex items-center gap-2 text-4xl font-medium tracking-tight" :class="positive ? 'text-good' : 'text-bad'">
          <component :is="positive ? TrendingUp : TrendingDown" class="h-7 w-7" aria-hidden="true" />
          {{ signedMoney(result.monthly_cash_flow) }}
        </p>
        <p class="mt-1 text-xs text-text-2">
          {{ positive ? 'Rent covers every cost' : 'You would top up this much each month' }}
          · {{ signedMoney(result.annual_cash_flow) }}/yr
        </p>
      </div>
      <div class="text-right">
        <p class="text-xs text-muted">Cash to close</p>
        <p class="num mt-1 text-xl">{{ moneyShort(result.cash_invested) }}</p>
        <p class="text-xs text-text-2">{{ moneyShort(result.down_payment) }} down + {{ moneyShort(result.closing_costs) }} closing</p>
      </div>
    </div>

    <dl v-if="result" class="mt-6 grid grid-cols-2 gap-x-6 gap-y-4 border-y border-border py-4 sm:grid-cols-5">
      <Stat label="Cap rate" :value="pct(result.cap_rate_pct, 2)" sub="NOI ÷ price" />
      <Stat label="Cash-on-cash" :value="pct(result.cash_on_cash_pct)" sub="Cash flow ÷ cash in" />
      <Stat label="Debt coverage" :value="result.dscr === null ? '—' : `${num(result.dscr, 2)}×`" sub="Lenders want ≥ 1.2×" />
      <Stat label="Break-even rent" :value="moneyShort(result.break_even_rent)" sub="for $0 cash flow" />
      <Stat label="Equity built, yr 1" :value="moneyShort(result.principal_paydown_year1)" sub="Principal repaid" />
    </dl>

    <!-- Where the rent goes -->
    <div v-if="result" class="mt-5">
      <p class="mb-3 text-xs text-muted">Where the rent goes each month</p>
      <div class="space-y-2 text-xs">
        <div class="grid grid-cols-[9.5rem_1fr_5rem] items-center gap-3">
          <span class="text-text">Rent{{ inputs.other_income_monthly ? ' + other income' : '' }}</span>
          <div class="h-2.5 rounded-sm bg-accent" :style="{ width: incomeWidth }" />
          <span class="num text-right">{{ money(result.gross_monthly_income) }}</span>
        </div>
        <div v-for="row in flows" :key="row.label" class="grid grid-cols-[9.5rem_1fr_5rem] items-center gap-3">
          <span class="text-text-2">{{ row.label }}</span>
          <div class="h-2.5 rounded-sm bg-border-strong" :style="{ width: row.width }" />
          <span class="num text-right text-text-2">{{ money(row.value) }}</span>
        </div>
      </div>
    </div>

    <ul v-if="result?.warnings.length" class="mt-5 space-y-1.5">
      <li v-for="w in result.warnings" :key="w" class="flex gap-2 text-xs text-warn">
        <AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>{{ w }}</span>
      </li>
    </ul>

    <!-- Assumptions -->
    <div class="mt-6 border-t border-border pt-5">
      <div class="mb-4 flex items-center gap-2">
        <p class="text-sm font-medium">Your assumptions</p>
        <InfoTip text="Defaults come from the listing (tax, condo fee), a city rent benchmark and the Bank of Canada posted rate. Every one is an estimate — change them to match your quote, lease and insurance." />
      </div>
      <div class="grid gap-x-8 gap-y-5 sm:grid-cols-2">
        <SliderField v-model="inputs.price" label="Purchase price" :min="Math.round(priceBase * 0.6)" :max="Math.round(priceBase * 1.2)" :step="1000" prefix="$" />
        <SliderField
          v-model="inputs.monthly_rent" label="Monthly rent" :min="0" :max="Math.max(6000, Math.round(initial.monthly_rent * 2))" :step="25" prefix="$"
          :hint="rent ? `Benchmark ${money(rent.monthly_rent)} for ${rent.bedrooms === 3 ? '3+' : rent.bedrooms}-bed in ${rent.city}. Averages include long tenancies; asking rent for a vacant unit is usually higher.` : 'No rent benchmark for this city — enter the rent you expect.'"
        />
        <SliderField v-model="inputs.down_payment_pct" label="Down payment" :min="5" :max="100" :step="1" suffix="%" hint="Rental properties generally need 20% down." />
        <SliderField
          v-model="inputs.interest_rate_pct" label="Mortgage rate" :min="0" :max="10" :step="0.05" suffix="%"
          :hint="rate ? `Default is the Bank of Canada posted 5-year rate (${rate.date}). Negotiated rates are usually lower.` : undefined"
        />
        <SliderField v-model="inputs.amortization_years" label="Amortization" :min="5" :max="35" :step="1" suffix="yr" />
        <SliderField v-model="inputs.vacancy_pct" label="Vacancy" :min="0" :max="20" :step="0.5" suffix="%" />
        <SliderField v-model="inputs.property_tax_annual" label="Property tax" :min="0" :max="30000" :step="50" prefix="$" suffix="/yr" />
        <SliderField v-model="inputs.condo_fee_monthly" label="Condo fee" :min="0" :max="2000" :step="10" prefix="$" suffix="/mo" />
        <SliderField v-model="inputs.insurance_monthly" label="Insurance" :min="0" :max="500" :step="5" prefix="$" suffix="/mo" />
        <SliderField v-model="inputs.maintenance_pct" label="Maintenance reserve" :min="0" :max="20" :step="0.5" suffix="% of rent" />
        <SliderField v-model="inputs.management_pct" label="Property management" :min="0" :max="15" :step="0.5" suffix="% of rent" />
      </div>
      <p v-if="result" class="mt-4 text-[11px] leading-relaxed text-muted">
        Closing costs: {{ result.closing_costs_note }}. Mortgage compounds semi-annually (Canadian fixed rates).
        <template v-if="result.insurance_premium > 0"> Includes a {{ money(result.insurance_premium) }} mortgage insurance premium.</template>
      </p>
    </div>
    <slot name="actions" />
  </div>
</template>
