<script setup lang="ts">
/**
 * The app's cash-flow calculator, running in the page. Same maths as
 * shared/analytics/cashflow.py (kept in sync by shared fixtures). The scenario is
 * mirrored into the URL so it can be shared.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { compute } from '../lib/cashflow.js'

type Inputs = {
  city: string
  price: number
  monthly_rent: number
  down_payment_pct: number
  interest_rate_pct: number
  amortization_years: number
  vacancy_pct: number
  property_tax_annual: number
  condo_fee_monthly: number
  insurance_monthly: number
  maintenance_pct: number
  management_pct: number
}

const PRESETS: Record<string, Inputs> = {
  'Toronto condo': {
    city: 'Toronto', price: 650000, monthly_rent: 2900, down_payment_pct: 20, interest_rate_pct: 4.5,
    amortization_years: 25, vacancy_pct: 4, property_tax_annual: 3900, condo_fee_monthly: 520,
    insurance_monthly: 35, maintenance_pct: 5, management_pct: 0,
  },
  'Calgary townhouse': {
    city: 'Calgary', price: 420000, monthly_rent: 2300, down_payment_pct: 20, interest_rate_pct: 4.5,
    amortization_years: 25, vacancy_pct: 4, property_tax_annual: 2700, condo_fee_monthly: 380,
    insurance_monthly: 35, maintenance_pct: 5, management_pct: 0,
  },
  'Vancouver house': {
    city: 'Vancouver', price: 1250000, monthly_rent: 4800, down_payment_pct: 25, interest_rate_pct: 4.5,
    amortization_years: 25, vacancy_pct: 4, property_tax_annual: 4300, condo_fee_monthly: 0,
    insurance_monthly: 125, maintenance_pct: 8, management_pct: 0,
  },
}
const CITIES = ['Toronto', 'Ottawa', 'Vancouver', 'Calgary', 'Edmonton', 'Montreal', 'Winnipeg']

const inp = reactive<Inputs>({ ...PRESETS['Toronto condo'] })
const active = ref('Toronto condo')
const r = computed(() => compute({ ...inp }))

const cad = new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD', maximumFractionDigits: 0 })
const money = (v: number | null) => (v === null ? '—' : cad.format(v))
const signed = (v: number) => (v > 0 ? '+' : v < 0 ? '−' : '') + cad.format(Math.abs(v))
const pct = (v: number) => `${v.toFixed(2)}%`

// Where the effective rent goes, per month (bars scaled to gross income)
const breakdown = computed(() => {
  const e = r.value.monthly_expenses
  const rows = [
    ['Mortgage payment', r.value.monthly_mortgage_payment],
    ['Property tax', e.property_tax],
    ['Condo fee', e.condo_fee],
    ['Insurance', e.insurance],
    ['Maintenance reserve', e.maintenance],
    ['Management', e.management],
    ['Vacancy allowance', r.value.gross_monthly_income - r.value.effective_monthly_income],
  ] as [string, number][]
  const scale = Math.max(r.value.gross_monthly_income, ...rows.map(([, v]) => v), 1)
  return rows.filter(([, v]) => v > 0).map(([label, v]) => ({ label, v, w: (v / scale) * 100 }))
})

function apply(name: string) {
  Object.assign(inp, PRESETS[name])
  active.value = name
}

const FIELDS = Object.keys(PRESETS['Toronto condo']) as (keyof Inputs)[]
onMounted(() => {
  const q = new URLSearchParams(location.search)
  if (!q.has('price')) return
  for (const k of FIELDS) {
    const v = q.get(k)
    if (v === null) continue
    ;(inp as any)[k] = k === 'city' ? v : Number(v)
  }
  active.value = ''
})
watch(
  inp,
  () => {
    const q = new URLSearchParams(FIELDS.map((k) => [k, String(inp[k])]))
    history.replaceState(history.state, '', `${location.pathname}?${q}`)
  },
  { deep: true },
)
const copied = ref(false)
async function share() {
  await navigator.clipboard?.writeText(location.href)
  copied.value = true
  setTimeout(() => (copied.value = false), 1600)
}
</script>

<template>
  <div class="calc">
    <div class="presets" role="group" aria-label="Example scenarios">
      <button v-for="(_, name) in PRESETS" :key="name" type="button" :aria-pressed="active === name" @click="apply(name as string)">
        {{ name }}
      </button>
      <button type="button" class="share" @click="share">{{ copied ? 'Link copied' : 'Copy link to this scenario' }}</button>
    </div>

    <div class="grid">
      <fieldset @input="active = ''">
        <legend>Property</legend>
        <label>City
          <select v-model="inp.city"><option v-for="c in CITIES" :key="c">{{ c }}</option></select>
        </label>
        <label>Price <span class="unit">$</span><input v-model.number="inp.price" type="number" min="50000" step="5000" /></label>
        <label>Rent <span class="unit">$ / month</span><input v-model.number="inp.monthly_rent" type="number" min="0" step="50" /></label>
        <label>Property tax <span class="unit">$ / year</span><input v-model.number="inp.property_tax_annual" type="number" min="0" step="100" /></label>
        <label>Condo fee <span class="unit">$ / month</span><input v-model.number="inp.condo_fee_monthly" type="number" min="0" step="10" /></label>
        <label>Insurance <span class="unit">$ / month</span><input v-model.number="inp.insurance_monthly" type="number" min="0" step="5" /></label>
      </fieldset>

      <fieldset @input="active = ''">
        <legend>Financing and costs</legend>
        <label>Down payment <span class="unit">{{ inp.down_payment_pct }}%</span>
          <input v-model.number="inp.down_payment_pct" type="range" min="5" max="50" step="1" />
        </label>
        <label>Interest rate <span class="unit">{{ inp.interest_rate_pct.toFixed(2) }}%</span>
          <input v-model.number="inp.interest_rate_pct" type="range" min="1" max="9" step="0.05" />
        </label>
        <label>Amortization <span class="unit">{{ inp.amortization_years }} years</span>
          <input v-model.number="inp.amortization_years" type="range" min="10" max="30" step="5" />
        </label>
        <label>Vacancy <span class="unit">{{ inp.vacancy_pct }}% of rent</span>
          <input v-model.number="inp.vacancy_pct" type="range" min="0" max="15" step="1" />
        </label>
        <label>Maintenance <span class="unit">{{ inp.maintenance_pct }}% of rent</span>
          <input v-model.number="inp.maintenance_pct" type="range" min="0" max="15" step="1" />
        </label>
        <label>Management <span class="unit">{{ inp.management_pct }}% of rent</span>
          <input v-model.number="inp.management_pct" type="range" min="0" max="12" step="1" />
        </label>
      </fieldset>

      <section class="out" aria-live="polite">
        <p class="kicker">Monthly cash flow</p>
        <p class="hero niq-num" :class="r.monthly_cash_flow >= 0 ? 'pos' : 'neg'">
          {{ signed(r.monthly_cash_flow) }}
          <span>{{ r.monthly_cash_flow >= 0 ? 'positive' : 'negative' }}</span>
        </p>
        <dl class="stats niq-num">
          <div><dt>Cap rate</dt><dd>{{ pct(r.cap_rate_pct) }}</dd></div>
          <div><dt>Cash-on-cash</dt><dd>{{ pct(r.cash_on_cash_pct) }}</dd></div>
          <div><dt>DSCR</dt><dd>{{ r.dscr ?? '—' }}</dd></div>
          <div><dt>Break-even rent</dt><dd>{{ money(r.break_even_rent) }}</dd></div>
          <div><dt>Cash to close</dt><dd>{{ money(r.cash_invested) }}</dd></div>
          <div><dt>Year-1 equity</dt><dd>{{ money(r.principal_paydown_year1) }}</dd></div>
        </dl>
        <p class="note">
          Mortgage {{ money(r.monthly_mortgage_payment) }}/month on {{ money(r.mortgage_principal) }}<template v-if="r.insurance_premium">
            (includes {{ money(r.insurance_premium) }} CMHC premium)</template>.
          Closing costs {{ money(r.closing_costs) }}: {{ r.closing_costs_note }}.
        </p>
        <ul v-if="r.warnings.length" class="warnings">
          <li v-for="w in r.warnings" :key="w">{{ w }}</li>
        </ul>
      </section>
    </div>

    <table class="where">
      <caption>Where the rent goes each month ({{ money(r.gross_monthly_income) }} gross)</caption>
      <tbody>
        <tr v-for="row in breakdown" :key="row.label">
          <th scope="row">{{ row.label }}</th>
          <td class="bar"><span :style="{ width: `${row.w}%` }" /></td>
          <td class="niq-num">{{ money(row.v) }}</td>
        </tr>
        <tr class="total">
          <th scope="row">Left over</th>
          <td class="bar" />
          <td class="niq-num" :class="r.monthly_cash_flow >= 0 ? 'pos' : 'neg'">{{ signed(r.monthly_cash_flow) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.calc {
  margin: 24px 0;
  border: 1px solid var(--vp-c-divider);
  border-radius: 14px;
  padding: 20px;
  background: var(--vp-c-bg-soft);
}
.presets {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.presets button {
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  background: var(--vp-c-bg);
  transition: border-color 0.2s, color 0.2s;
}
.presets button[aria-pressed='true'] {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}
.presets .share {
  margin-left: auto;
  color: var(--vp-c-text-2);
}
.presets button:focus-visible,
input:focus-visible,
select:focus-visible {
  outline: 2px solid var(--vp-c-brand-1);
  outline-offset: 2px;
}
.grid {
  display: grid;
  gap: 20px;
  grid-template-columns: 1fr;
}
@media (min-width: 900px) {
  .grid {
    grid-template-columns: 1fr 1fr 1.15fr;
  }
}
fieldset {
  border: 0;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
  align-content: start;
}
legend {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--vp-c-text-2);
  margin-bottom: 4px;
}
label {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 8px;
  font-size: 14px;
  align-items: center;
}
label > input,
label > select {
  grid-column: 1 / -1;
}
.unit {
  color: var(--vp-c-text-2);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}
input[type='number'],
select {
  width: 100%;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  padding: 6px 10px;
  background: var(--vp-c-bg);
  font-variant-numeric: tabular-nums;
}
input[type='range'] {
  width: 100%;
  accent-color: var(--vp-c-brand-1);
}
.out {
  border-left: 1px solid var(--vp-c-divider);
  padding-left: 20px;
}
@media (max-width: 899px) {
  .out {
    border-left: 0;
    padding-left: 0;
    border-top: 1px solid var(--vp-c-divider);
    padding-top: 16px;
  }
}
.kicker {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--vp-c-text-2);
}
.hero {
  margin: 4px 0 12px;
  font-size: 40px;
  line-height: 1.1;
  font-weight: 650;
  letter-spacing: -0.02em;
}
.hero span {
  display: block;
  margin-top: 2px;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0;
  color: var(--vp-c-text-2);
}
.pos {
  color: var(--niq-good);
}
.neg {
  color: var(--niq-bad);
}
.stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px 16px;
  margin: 0;
}
.stats dt {
  font-size: 12px;
  color: var(--vp-c-text-2);
}
.stats dd {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.note {
  font-size: 13px;
  color: var(--vp-c-text-2);
  line-height: 1.5;
}
.warnings {
  font-size: 13px;
  color: var(--vp-c-text-2);
  padding-left: 18px;
}
.where {
  display: table;
  width: 100%;
  margin: 20px 0 0;
  border-collapse: collapse;
}
.where caption {
  text-align: left;
  font-size: 13px;
  color: var(--vp-c-text-2);
  padding-bottom: 6px;
}
.where tr {
  background: transparent !important;
  border: 0;
}
.where th,
.where td {
  border: 0;
  padding: 4px 8px 4px 0;
  font-size: 14px;
}
.where th {
  font-weight: 500;
  text-align: left;
  white-space: nowrap;
  width: 1%;
}
.where td.bar {
  width: 100%;
}
.where td.bar span {
  display: block;
  height: 10px;
  border-radius: 0 4px 4px 0;
  background: var(--vp-c-brand-3);
  transition: width 0.3s ease;
  min-width: 2px;
}
.where td:last-child {
  text-align: right;
  white-space: nowrap;
}
.where .total th,
.where .total td {
  border-top: 1px solid var(--vp-c-divider);
  font-weight: 600;
}
</style>
