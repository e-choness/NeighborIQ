// API contract (mirrors services/api/openapi.json)

export interface User {
  id: number
  email: string
  name: string | null
  role: 'user' | 'admin'
}

export type PropertyType = 'condo' | 'townhouse' | 'semi' | 'detached'

export interface Listing {
  id: number
  title: string
  community: string | null
  city: string
  region: string
  street: string | null
  postal_code: string | null
  property_type: PropertyType | null
  price: number
  sqft: number | null
  rooms: number | null
  bathrooms: number | null
  parking: number | null
  age: number | null
  condo_fee: number | null
  property_tax: number | null
  status: string
  listed_at: string | null
  latitude: number | null
  longitude: number | null
  images: string[] | null
  source: string | null
  is_synthetic: boolean
  price_per_sqft: number | null
  days_on_market: number | null
  original_price: number | null
  price_cut_pct: number | null
  gross_yield_pct: number | null
  cap_rate_pct: number | null
}

export interface ListingPage {
  total: number
  page: number
  page_size: number
  items: Listing[]
}

export interface Comp {
  house_id: number
  title: string
  community: string | null
  price: number
  sqft: number
  rooms: number | null
  price_per_sqft: number
  distance_m: number
  latitude: number
  longitude: number
}

export interface Valuation {
  method: string
  basis: string
  asking_price: number
  fair_value: number
  fair_value_low: number
  fair_value_high: number
  median_price_per_sqft: number
  subject_price_per_sqft: number
  delta_pct: number
  verdict: 'below' | 'in_line' | 'above'
  confidence: 'high' | 'medium' | 'low'
  radius_m: number
  comps: Comp[]
}

export interface RentEstimate {
  monthly_rent: number
  bedrooms: number
  city: string
  source: string
  survey_date: string | null
  note: string
}

export interface CashFlowInput {
  price: number
  monthly_rent: number
  city: string
  down_payment_pct: number
  interest_rate_pct: number
  amortization_years: number
  vacancy_pct: number
  property_tax_annual: number
  condo_fee_monthly: number
  insurance_monthly: number
  maintenance_pct: number
  management_pct: number
  other_income_monthly: number
  closing_costs: number | null
}

export interface CashFlowResult {
  down_payment: number
  insurance_premium: number
  mortgage_principal: number
  monthly_mortgage_payment: number
  closing_costs: number
  closing_costs_note: string
  cash_invested: number
  gross_monthly_income: number
  effective_monthly_income: number
  monthly_expenses: Record<'property_tax' | 'condo_fee' | 'insurance' | 'maintenance' | 'management', number>
  monthly_operating_expenses: number
  noi_annual: number
  monthly_cash_flow: number
  annual_cash_flow: number
  cap_rate_pct: number
  gross_yield_pct: number
  cash_on_cash_pct: number
  dscr: number | null
  break_even_rent: number | null
  principal_paydown_year1: number
  warnings: string[]
}

export interface RateContext {
  rate_pct: number
  series: string
  label: string
  date: string
  note: string
}

export interface StatValue { value: number | null; period: string | null }

export interface AreaContext { id: number; name: string; stats: Record<string, StatValue> }

export interface Insights {
  house_id: number
  is_synthetic: boolean
  area: AreaContext | null
  rate: RateContext | null
  valuation: Valuation | null
  rent: RentEstimate | null
  cash_flow: { inputs: CashFlowInput; result: CashFlowResult } | null
  ml: { predicted_price: number; price_low: number; price_high: number; coverage: number; model_version: string } | null
}

export interface Market {
  city: string
  listing_count: number
  median_price: number | null
  median_price_per_sqft: number | null
  median_gross_yield_pct: number | null
  median_cap_rate_pct: number | null
  price_cut_share_pct: number | null
  median_days_on_market: number | null
  synthetic_share_pct: number
  latitude: number | null
  longitude: number | null
}

export interface MarketPoints {
  city: string
  columns: string[]
  rows: (number | null)[][]
}

export interface PricePoint { price: number; recorded_at: string }

export interface Poi { name: string; detail: string | null; distance_m: number; latitude: number | null; longitude: number | null }

export interface Neighbourhood {
  house_id: number
  attribution: string
  loaded: boolean
  schools: Poi[]
  transit: Poi[]
  hospitals: Poi[]
}

export interface Indicator {
  series: string
  label: string
  unit: string
  source: string
  latest: number
  date: string
  history: { date: string; value: number }[]
}

export interface DataSource {
  source: string
  loaded_at: string
  row_count: number | null
  licence: string
  attribution: string | null
}

export interface PropertyRecord {
  id: number
  city: string
  address: string
  postal_code: string | null
  latitude: number | null
  longitude: number | null
  property_class: string | null
  zoning: string | null
  year_built: number | null
  units: number | null
  floor_area_sqft: number | null
  lot_size_sqft: number | null
  assessed_value: number | null
  tax_levy: number | null
  assessment_year: number | null
  area_name: string | null
}

export interface SavedDeal {
  id: number
  house_id: number
  saved_at: string
  notes: string | null
  assumptions: Partial<CashFlowInput> | null
  house: Listing
}

export interface AdminStatus {
  coverage: Record<string, number | null>
  open_data_loads: { source: string; loaded_at: string; row_count: number | null; licence: string; status: string; message: string | null }[]
  broker: 'up' | 'down'
  workers: string[]
}
