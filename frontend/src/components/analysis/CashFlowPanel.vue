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
const metrics = computed(() => {
  const r = result.value
  if (!r) return []
  return [
    { label: 'Cap rate', value: pct(r.cap_rate_pct, 2), sub: 'NOI ÷ price' },
    { label: 'Cash-on-cash', value: pct(r.cash_on_cash_pct), sub: 'Cash flow ÷ cash in' },
    { label: 'Debt coverage', value: r.dscr === null ? '—' : `${num(r.dscr, 2)}×`, sub: 'Lenders want ≥ 1.2×' },
    { label: 'Break-even rent', value: money(r.break_even_rent), sub: 'for $0 cash flow' },
    { label: 'Equity built, yr 1', value: moneyShort(r.principal_paydown_year1), sub: 'Principal repaid' },
    { label: 'Gross yield', value: pct(r.gross_yield_pct), sub: 'Rent ÷ price' },
  ]
})

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
    <div v-if="result" class="flex items-end justify-between gap-3" :class="{ 'opacity-70 transition-opacity': isLoading }">
      <div>
        <p class="text-xs text-muted">Monthly cash flow after mortgage</p>
        <p data-testid="monthly-cash-flow" class="num my-1 flex items-center gap-2 text-[34px] font-medium tracking-[-0.03em]" :class="positive ? 'text-good' : 'text-bad'">
          <component :is="positive ? TrendingUp : TrendingDown" class="h-6 w-6" aria-hidden="true" />
          {{ signedMoney(result.monthly_cash_flow) }}
        </p>
        <p class="text-xs text-text-2">
          {{ positive ? 'Surplus each month' : 'You would top up this much each month' }}
          · {{ signedMoney(result.annual_cash_flow) }}/yr
        </p>
      </div>
      <div class="text-right">
        <p class="text-xs text-muted">Cash to close</p>
        <p class="num mt-1 text-xl font-medium">{{ moneyShort(result.cash_invested) }}</p>
        <p class="text-[11px] text-text-2">{{ moneyShort(result.down_payment) }} down + {{ moneyShort(result.closing_costs) }} closing</p>
      </div>
    </div>

    <dl v-if="result" class="mt-[18px] grid grid-cols-3 gap-x-2.5 gap-y-3.5 border-y border-border py-3.5">
      <div v-for="m in metrics" :key="m.label" class="min-w-0">
        <dt class="text-[11px] text-muted">{{ m.label }}</dt>
        <dd class="num mt-[3px] truncate text-base font-medium">{{ m.value }}</dd>
        <p class="mt-0.5 truncate text-[11px] text-text-2">{{ m.sub }}</p>
      </div>
    </dl>

    <!-- Where the rent goes -->
    <div v-if="result" class="mt-4">
      <p class="text-xs text-muted">Where the rent goes each month</p>
      <div class="mt-2 flex flex-col gap-[7px] text-xs">
        <div class="grid grid-cols-[8rem_1fr_4rem] items-center gap-2.5">
          <span class="text-text-2">Rent{{ inputs.other_income_monthly ? ' + other' : '' }}</span>
          <span class="h-[7px] rounded-[9px] bg-surface-2"><span class="block h-full rounded-[9px] bg-accent" :style="{ width: incomeWidth }" /></span>
          <span class="num text-right">{{ money(result.gross_monthly_income) }}</span>
        </div>
        <div v-for="row in flows" :key="row.label" class="grid grid-cols-[8rem_1fr_4rem] items-center gap-2.5">
          <span class="text-text-2">{{ row.label }}</span>
          <span class="h-[7px] rounded-[9px] bg-surface-2"><span class="block h-full rounded-[9px] bg-bar" :style="{ width: row.width }" /></span>
          <span class="num text-right">{{ money(row.value) }}</span>
        </div>
      </div>
    </div>

    <ul v-if="result?.warnings.length" class="mt-3 space-y-1.5">
      <li v-for="w in result.warnings" :key="w" class="flex gap-1.5 text-xs text-warn">
        <AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        <span>{{ w }}</span>
      </li>
    </ul>
    <p v-else-if="result && !positive" class="mt-3 flex items-center gap-1.5 text-xs text-warn">
      <AlertTriangle class="h-3.5 w-3.5 shrink-0" aria-hidden="true" /> Negative monthly cash flow at these assumptions.
    </p>

    <!-- Assumptions -->
    <div class="mt-5">
      <div class="flex items-center gap-2">
        <p class="text-sm font-medium">Your assumptions</p>
        <InfoTip text="Defaults come from the listing (tax, condo fee), a city rent benchmark and the Bank of Canada posted rate. Every one is an estimate — change them to match your quote, lease and insurance." />
      </div>
      <div class="mt-2.5 grid grid-cols-2 gap-x-[18px] gap-y-3.5">
        <SliderField v-model="inputs.price" label="Purchase price" :min="Math.round(priceBase * 0.6)" :max="Math.round(priceBase * 1.2)" :step="1000" prefix="$" />
        <SliderField v-model="inputs.monthly_rent" label="Monthly rent" :min="0" :max="Math.max(6000, Math.round(initial.monthly_rent * 2))" :step="25" prefix="$" />
        <SliderField v-model="inputs.down_payment_pct" label="Down payment" :min="5" :max="100" :step="1" suffix="%" />
        <SliderField v-model="inputs.interest_rate_pct" label="Mortgage rate" :min="0" :max="10" :step="0.05" suffix="%" />
        <SliderField v-model="inputs.amortization_years" label="Amortization" :min="5" :max="35" :step="1" suffix="yr" />
        <SliderField v-model="inputs.vacancy_pct" label="Vacancy" :min="0" :max="20" :step="0.5" suffix="%" />
        <SliderField v-model="inputs.property_tax_annual" label="Property tax" :min="0" :max="30000" :step="50" prefix="$" suffix="/yr" />
        <SliderField v-model="inputs.condo_fee_monthly" label="Condo fee" :min="0" :max="2000" :step="10" prefix="$" suffix="/mo" />
        <SliderField v-model="inputs.insurance_monthly" label="Insurance" :min="0" :max="500" :step="5" prefix="$" suffix="/mo" />
        <SliderField v-model="inputs.maintenance_pct" label="Maintenance reserve" :min="0" :max="20" :step="0.5" suffix="% rent" />
        <SliderField v-model="inputs.management_pct" label="Property management" :min="0" :max="15" :step="0.5" suffix="% rent" />
      </div>
      <p class="mt-4 text-[11px] leading-normal text-muted">
        {{ rent ? `Rent benchmark ${money(rent.monthly_rent)} for ${rent.bedrooms === 3 ? '3+' : rent.bedrooms}-bed in ${rent.city}; asking rent for a vacant unit is usually higher.` : 'No rent benchmark for this city — enter the rent you expect.' }}
        <template v-if="rate"> Rate default: Bank of Canada posted 5-year ({{ rate.date }}); negotiated rates are usually lower.</template>
      </p>
      <p v-if="result" class="mt-2 text-[11px] leading-normal text-muted">
        Closing costs: {{ result.closing_costs_note }}. Mortgage compounds semi-annually (Canadian fixed rates).
        <template v-if="result.insurance_premium > 0"> Includes a {{ money(result.insurance_premium) }} mortgage insurance premium.</template>
      </p>
    </div>
    <slot name="actions" />
  </div>
</template>
