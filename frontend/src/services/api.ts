import axios from 'axios'
import type {
  House,
  HouseListResponse,
  HouseFilters,
  Community,
  HouseInsights,
  NeighborhoodAnalysis,
  LoginCredentials,
  SignupCredentials,
  User,
} from '@/types'

// All calls go to /api which nginx proxies to api-gateway:8000
// In dev mode, vite.config.ts proxies /api to localhost:8000
const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // send HttpOnly cookies automatically
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor — handle 401 globally
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh the token once
      const originalRequest = error.config
      if (!originalRequest._retried) {
        originalRequest._retried = true
        try {
          await api.post('/auth/refresh')
          return api(originalRequest)
        } catch {
          // Refresh failed — clear auth state (handled by store)
          window.dispatchEvent(new CustomEvent('auth:expired'))
        }
      }
    }
    return Promise.reject(error)
  }
)

// ============================================================================
// Auth API
// ============================================================================

export const authApi = {
  login: (credentials: LoginCredentials) =>
    api.post<User>('/auth/login', credentials),

  signup: (credentials: SignupCredentials) =>
    api.post<User>('/auth/signup', credentials),

  logout: () => api.post('/auth/logout'),

  me: () => api.get<User>('/auth/me'),

  refresh: () => api.post('/auth/refresh'),
}

// ============================================================================
// Houses API
// ============================================================================

export const housesApi = {
  list: (filters: Partial<HouseFilters> = {}) =>
    api.get<HouseListResponse>('/houses', { params: filters }),

  get: (id: number) =>
    api.get<House>(`/houses/${id}`),

  create: (house: Omit<House, 'id' | 'created_at' | 'updated_at'>) =>
    api.post<House>('/houses', house),

  update: (id: number, house: Partial<House>) =>
    api.put<House>(`/houses/${id}`, house),

  delete: (id: number) =>
    api.delete(`/houses/${id}`),

  search: (q: string, city?: string, region?: string) =>
    api.get<{ items: House[] }>('/houses/search', { params: { q, city, region } }),

  communities: (city?: string, region?: string) =>
    api.get<{ items: Community[] }>('/communities', { params: { city, region } }),

  communityStats: (communityId: number) =>
    api.get(`/communities/${communityId}/stats`),
}

// ============================================================================
// AI Insights API (direct to ai-insights-service via gateway if routed,
// otherwise we fall back to the house service proxy path)
// ============================================================================

export const insightsApi = {
  houseInsights: (houseId: number) =>
    api.get<HouseInsights>(`/houses/${houseId}/insights`),

  neighborhoodAnalysis: (city: string, region: string) =>
    api.get<NeighborhoodAnalysis>(`/neighborhoods/${city}/${region}/analysis`),
}

// ============================================================================
// Search API
// ============================================================================

export const searchApi = {
  fulltext: (q: string, filters: Record<string, unknown> = {}) =>
    api.get('/search', { params: { q, ...filters } }),

  nearby: (lat: number, lon: number, radius = 5) =>
    api.get('/search/nearby', { params: { lat, lon, radius } }),
}

export default api
