// JavaScript port of shared/analytics/cashflow.py for the interactive calculator
// in the docs. Kept in lockstep by cashflow.fixtures.json: shared/tests checks the
// fixtures against the Python, docs/scripts/check-cashflow.mjs against this file.

const INSURANCE_PREMIUMS = [
  [0.85, 0.028],
  [0.9, 0.031],
  [0.95, 0.04],
]
export const INSURED_PRICE_CAP = 1_500_000

const ONTARIO_LTT = [
  [0, 0.005],
  [55_000, 0.01],
  [250_000, 0.015],
  [400_000, 0.02],
  [2_000_000, 0.025],
]
const BC_PTT = [
  [0, 0.01],
  [200_000, 0.02],
  [2_000_000, 0.03],
  [3_000_000, 0.05],
]
const QUEBEC_WELCOME = [
  [0, 0.005],
  [61_500, 0.01],
  [307_800, 0.015],
  [552_300, 0.02],
  [1_104_700, 0.025],
  [2_136_500, 0.035],
]
const CITY_PROVINCE = {
  toronto: 'ON',
  ottawa: 'ON',
  mississauga: 'ON',
  hamilton: 'ON',
  vancouver: 'BC',
  burnaby: 'BC',
  victoria: 'BC',
  calgary: 'AB',
  edmonton: 'AB',
  montreal: 'QC',
  montréal: 'QC',
  quebec: 'QC',
  winnipeg: 'MB',
}

export const DEFAULTS = {
  price: 0,
  monthly_rent: 0,
  city: '',
  down_payment_pct: 20,
  interest_rate_pct: 4.5,
  amortization_years: 25,
  vacancy_pct: 4,
  property_tax_annual: 0,
  condo_fee_monthly: 0,
  insurance_monthly: 0,
  maintenance_pct: 5,
  management_pct: 0,
  other_income_monthly: 0,
  closing_costs: null,
}

function bracketed(price, brackets) {
  let tax = 0
  brackets.forEach(([threshold, rate], i) => {
    const upper = i + 1 < brackets.length ? brackets[i + 1][0] : Infinity
    if (price > threshold) tax += (Math.min(price, upper) - threshold) * rate
  })
  return tax
}

export function landTransferTax(price, city) {
  const key = (city || '').trim().toLowerCase()
  const province = CITY_PROVINCE[key]
  if (province === 'ON') {
    const tax = bracketed(price, ONTARIO_LTT)
    if (key === 'toronto') return [tax * 2, 'Ontario LTT + Toronto municipal LTT (same brackets up to $3M)']
    return [tax, 'Ontario land transfer tax']
  }
  if (province === 'BC') return [bracketed(price, BC_PTT), 'BC property transfer tax']
  if (province === 'QC') return [bracketed(price, QUEBEC_WELCOME), 'Québec welcome tax (approx. Montréal brackets)']
  if (province === 'AB') return [50 + (price / 5000) * 2, 'Alberta title registration fees (no LTT)']
  return [price * 0.015, 'Rough 1.5% estimate (province not modelled)']
}

export const monthlyRate = (annualRatePct) => (1 + annualRatePct / 100 / 2) ** (1 / 6) - 1

export function mortgagePayment(principal, annualRatePct, amortizationYears) {
  const n = amortizationYears * 12
  if (principal <= 0) return 0
  const i = monthlyRate(annualRatePct)
  if (i === 0) return principal / n
  return (principal * i) / (1 - (1 + i) ** -n)
}

export function insurancePremiumRate(ltv) {
  if (ltv <= 0.8) return 0
  for (const [cap, rate] of INSURANCE_PREMIUMS) if (ltv <= cap + 1e-9) return rate
  return INSURANCE_PREMIUMS[INSURANCE_PREMIUMS.length - 1][1]
}

// Python's round() rounds half to even; match it so fixtures compare exactly
function round(x, digits = 2) {
  const f = 10 ** digits
  const v = x * f
  const r = Math.round(v)
  const isHalf = Math.abs(v % 1) === 0.5
  return (isHalf && r % 2 !== 0 ? r - 1 : r) / f
}

export function compute(input) {
  const inp = { ...DEFAULTS, ...input }
  const warnings = []

  const down = (inp.price * inp.down_payment_pct) / 100
  const loan = inp.price - down
  const ltv = loan / inp.price
  const premium = loan * insurancePremiumRate(ltv)
  if (premium) {
    warnings.push(
      'Under 20% down requires mortgage default insurance; insured mortgages are ' +
        'generally only available for owner-occupied homes, not pure rentals.',
    )
    if (inp.price >= INSURED_PRICE_CAP)
      warnings.push('Insured mortgages are unavailable at $1.5M and above — 20% down required.')
  }
  const principal = loan + premium
  const payment = mortgagePayment(principal, inp.interest_rate_pct, inp.amortization_years)

  let closing, closingNote
  if (inp.closing_costs !== null && inp.closing_costs !== undefined) {
    closing = inp.closing_costs
    closingNote = 'Entered by user'
  } else {
    const [ltt, note] = landTransferTax(inp.price, inp.city)
    closing = ltt + 2000
    closingNote = `${note} + $2,000 legal/inspection (estimate)`
  }

  const grossIncome = inp.monthly_rent + inp.other_income_monthly
  const effectiveIncome = grossIncome * (1 - inp.vacancy_pct / 100)
  const expenses = {
    property_tax: inp.property_tax_annual / 12,
    condo_fee: inp.condo_fee_monthly,
    insurance: inp.insurance_monthly,
    maintenance: (inp.monthly_rent * inp.maintenance_pct) / 100,
    management: (inp.monthly_rent * inp.management_pct) / 100,
  }
  const opex = Object.values(expenses).reduce((a, b) => a + b, 0)
  const noiMonthly = effectiveIncome - opex
  const cashFlow = noiMonthly - payment
  const cashInvested = down + closing

  const annualDebt = payment * 12
  const variableShare = 1 - inp.vacancy_pct / 100 - (inp.maintenance_pct + inp.management_pct) / 100
  const fixed = expenses.property_tax + expenses.condo_fee + expenses.insurance + payment
  const other = inp.other_income_monthly * (1 - inp.vacancy_pct / 100)
  const breakEven = variableShare > 0 ? (fixed - other) / variableShare : null

  let balance = principal
  const i = monthlyRate(inp.interest_rate_pct)
  for (let k = 0; k < Math.min(12, inp.amortization_years * 12); k++) balance -= payment - balance * i

  if (inp.monthly_rent === 0) warnings.push('No rent entered — returns are meaningless until you add one.')
  if (cashFlow < 0) warnings.push('Negative monthly cash flow at these assumptions.')

  return {
    down_payment: round(down),
    insurance_premium: round(premium),
    mortgage_principal: round(principal),
    monthly_mortgage_payment: round(payment),
    closing_costs: round(closing),
    closing_costs_note: closingNote,
    cash_invested: round(cashInvested),
    gross_monthly_income: round(grossIncome),
    effective_monthly_income: round(effectiveIncome),
    monthly_expenses: Object.fromEntries(Object.entries(expenses).map(([k, v]) => [k, round(v)])),
    monthly_operating_expenses: round(opex),
    noi_annual: round(noiMonthly * 12),
    monthly_cash_flow: round(cashFlow),
    annual_cash_flow: round(cashFlow * 12),
    cap_rate_pct: round(((noiMonthly * 12) / inp.price) * 100),
    gross_yield_pct: round(((inp.monthly_rent * 12) / inp.price) * 100),
    cash_on_cash_pct: cashInvested ? round(((cashFlow * 12) / cashInvested) * 100) : 0,
    dscr: annualDebt ? round((noiMonthly * 12) / annualDebt) : null,
    break_even_rent: breakEven !== null ? round(breakEven) : null,
    principal_paydown_year1: round(principal - balance),
    warnings,
  }
}
