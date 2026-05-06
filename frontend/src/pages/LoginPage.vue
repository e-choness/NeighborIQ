<template>
  <div class="min-h-screen bg-slate-950 flex items-center justify-center p-4">
    <!-- Background gradient blobs -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="absolute -top-40 -right-40 w-80 h-80 bg-violet-600/20 rounded-full blur-3xl"></div>
      <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-cyan-600/10 rounded-full blur-3xl"></div>
    </div>

    <div class="relative w-full max-w-md">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center gap-2.5 mb-2">
          <div class="w-10 h-10 rounded-xl bg-violet-600 flex items-center justify-center">
            <svg class="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
          </div>
          <span class="text-2xl font-bold text-white">
            Neighbor<span class="text-violet-400">IQ</span>
          </span>
        </div>
        <p class="text-slate-400 text-sm">AI-powered Canadian real estate discovery</p>
      </div>

      <!-- Card -->
      <div class="bg-slate-800/80 backdrop-blur border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl">
        <!-- Tabs -->
        <div class="flex border-b border-slate-700/50">
          <button
            @click="tab = 'login'"
            class="flex-1 py-3.5 text-sm font-medium transition-colors"
            :class="tab === 'login'
              ? 'text-white border-b-2 border-violet-500'
              : 'text-slate-400 hover:text-white'"
          >
            Sign In
          </button>
          <button
            @click="tab = 'signup'"
            class="flex-1 py-3.5 text-sm font-medium transition-colors"
            :class="tab === 'signup'
              ? 'text-white border-b-2 border-violet-500'
              : 'text-slate-400 hover:text-white'"
          >
            Create Account
          </button>
        </div>

        <div class="p-6">
          <!-- Error banner -->
          <div
            v-if="authStore.error"
            class="mb-4 flex items-center gap-2 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg"
          >
            <svg class="w-4 h-4 text-red-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-sm text-red-300">{{ authStore.error }}</span>
          </div>

          <!-- Login form -->
          <form v-if="tab === 'login'" @submit.prevent="handleLogin" class="space-y-4">
            <div>
              <label class="form-label">Email address</label>
              <input
                v-model="loginForm.email"
                type="email"
                required
                autocomplete="email"
                placeholder="you@example.com"
                class="form-input"
              />
            </div>
            <div>
              <label class="form-label">Password</label>
              <div class="relative">
                <input
                  v-model="loginForm.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  autocomplete="current-password"
                  placeholder="••••••••"
                  class="form-input pr-10"
                />
                <button
                  type="button"
                  @click="showPassword = !showPassword"
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                >
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path v-if="showPassword" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path v-if="!showPassword" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
              </div>
            </div>
            <button
              type="submit"
              :disabled="authStore.loading"
              class="w-full py-2.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <div v-if="authStore.loading" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
              {{ authStore.loading ? 'Signing in...' : 'Sign In' }}
            </button>
          </form>

          <!-- Signup form -->
          <form v-else @submit.prevent="handleSignup" class="space-y-4">
            <div>
              <label class="form-label">Full name (optional)</label>
              <input
                v-model="signupForm.name"
                type="text"
                autocomplete="name"
                placeholder="Your name"
                class="form-input"
              />
            </div>
            <div>
              <label class="form-label">Email address</label>
              <input
                v-model="signupForm.email"
                type="email"
                required
                autocomplete="email"
                placeholder="you@example.com"
                class="form-input"
              />
            </div>
            <div>
              <label class="form-label">Password</label>
              <input
                v-model="signupForm.password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="new-password"
                placeholder="Min. 8 characters"
                minlength="8"
                class="form-input"
              />
            </div>
            <button
              type="submit"
              :disabled="authStore.loading"
              class="w-full py-2.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <div v-if="authStore.loading" class="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
              {{ authStore.loading ? 'Creating account...' : 'Create Account' }}
            </button>
          </form>

          <!-- Continue as guest -->
          <div class="mt-4 pt-4 border-t border-slate-700/50 text-center">
            <router-link to="/search" class="text-sm text-slate-400 hover:text-slate-200 transition-colors">
              Continue as guest →
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const tab = ref<'login' | 'signup'>(route.query.tab === 'signup' ? 'signup' : 'login')
const showPassword = ref(false)

const loginForm = reactive({ email: '', password: '' })
const signupForm = reactive({ email: '', password: '', name: '' })

watch(tab, () => authStore.clearError())

async function handleLogin() {
  try {
    await authStore.login(loginForm)
    const redirect = (route.query.redirect as string) || '/search'
    router.push(redirect)
  } catch {
    // error is shown via authStore.error
  }
}

async function handleSignup() {
  try {
    await authStore.signup(signupForm)
    router.push('/search')
  } catch {
    // error is shown via authStore.error
  }
}

onMounted(() => authStore.clearError())
</script>

<style scoped>
.form-label {
  @apply block text-xs font-medium text-slate-400 mb-1.5;
}
.form-input {
  @apply w-full bg-slate-700/50 border border-slate-600/50 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500/40 focus:border-violet-500/60 transition-all;
}
</style>
