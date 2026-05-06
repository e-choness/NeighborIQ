import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/services/api'
import type { User, LoginCredentials, SignupCredentials } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function checkAuth() {
    try {
      const response = await authApi.me()
      user.value = response.data
    } catch {
      user.value = null
    }
  }

  async function login(credentials: LoginCredentials) {
    loading.value = true
    error.value = null
    try {
      const response = await authApi.login(credentials)
      user.value = response.data
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      error.value = e.response?.data?.detail ?? 'Login failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function signup(credentials: SignupCredentials) {
    loading.value = true
    error.value = null
    try {
      const response = await authApi.signup(credentials)
      user.value = response.data
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      error.value = e.response?.data?.detail ?? 'Signup failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      user.value = null
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    checkAuth,
    login,
    signup,
    logout,
    clearError,
  }
})
