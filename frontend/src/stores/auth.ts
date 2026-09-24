import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/lib/api'
import type { User } from '@/lib/types'

export const useAuth = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const checked = ref(false)

  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function check() {
    if (checked.value) return
    try {
      user.value = await api<User>('/auth/me')
    } catch {
      user.value = null
    } finally {
      checked.value = true
    }
  }

  async function login(email: string, password: string) {
    user.value = await api<User>('/auth/login', { method: 'POST', body: { email, password } })
  }

  async function signup(email: string, password: string, name?: string) {
    user.value = await api<User>('/auth/signup', { method: 'POST', body: { email, password, name } })
  }

  async function logout() {
    await api('/auth/logout', { method: 'POST' }).catch(() => undefined)
    user.value = null
  }

  return { user, checked, isAuthenticated, isAdmin, check, login, signup, logout }
})
