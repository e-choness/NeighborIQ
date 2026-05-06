// ============================================================================
// Auth types
// ============================================================================

export interface User {
  id: number
  email: string
  name: string | null
  role: 'user' | 'admin'
  created_at: string
  updated_at: string | null
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface SignupCredentials {
  email: string
  password: string
  name?: string
}

// ============================================================================
// House types
// ============================================================================

export interface House {
  id: number
  title: string
  community: string
  city: string
  region: string
  street: string
  price: number
  area: number
  rooms: number
  floor: number | null
  decoration: string | null
  age: number | null
  latitude: number | null
  longitude: number | null
  url: string | null
  images: string[] | null
  created_at: string
  updated_at: string | null
}

export interface HouseListResponse {
  total: number
  page: number
  page_size: number
  items: House[]
}

export interface HouseFilters {
  city: string
  region: string
  price_min: number | null
  price_max: number | null
  rooms_min: number | null
  rooms_max: number | null
  area_min: number | null
  area_max: number | null
  page: number
  page_size: number
  sort: string
  order: 'asc' | 'desc'
}

// ============================================================================
// Community types
// ============================================================================

export interface Community {
  id: number
  name: string
  city: string
  region: string
  street: string
  latitude: number
  longitude: number
  house_count: number
  avg_price: number | null
}

// ============================================================================
// AI Insights types
// ============================================================================

export interface HouseInsights {
  house_id: number
  predicted_price: number | null
  price_low: number | null
  price_high: number | null
  confidence: number | null
  model_version: string | null
  annual_rent: number | null
  gross_yield: number | null
  net_yield: number | null
}

export interface NeighborhoodAnalysis {
  city: string
  region: string
  market_summary: string | null
  listing_count: number
  avg_gross_yield_pct: number
  avg_price_per_sqm: number
}

// ============================================================================
// Portfolio types
// ============================================================================

export interface SavedHouse {
  id: number
  house_id: number
  house: House
  saved_at: string
  notes: string | null
}

// ============================================================================
// Search types
// ============================================================================

export interface SearchResult {
  id: string
  title: string
  city: string
  region: string
  price: number
  area: number
  rooms: number
  location: { lat: number; lon: number } | null
  ai_score: number | null
}

// ============================================================================
// API response types
// ============================================================================

export interface ApiError {
  detail: string
  status: number
}

// ============================================================================
// Chart data types
// ============================================================================

export interface ChartDataPoint {
  label: string
  value: number
}

export interface PriceTrendData {
  labels: string[]
  prices: number[]
}
