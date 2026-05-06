<template>
  <nav class="fixed top-0 left-0 right-0 z-50 bg-slate-900/95 backdrop-blur border-b border-slate-700/50">
    <div class="max-w-screen-2xl mx-auto px-4 flex items-center justify-between h-16">
      <!-- Logo -->
      <router-link to="/search" class="flex items-center gap-2.5 group">
        <div class="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
        </div>
        <span class="text-white font-semibold text-lg tracking-tight">
          Neighbor<span class="text-violet-400">IQ</span>
        </span>
      </router-link>

      <!-- Center nav links -->
      <div class="hidden md:flex items-center gap-1">
        <router-link
          to="/search"
          class="nav-link"
          :class="{ 'nav-link-active': route.name === 'Search' }"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Discover
        </router-link>
        <router-link
          v-if="authStore.isAuthenticated"
          to="/portfolio"
          class="nav-link"
          :class="{ 'nav-link-active': route.name === 'Portfolio' }"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Portfolio
        </router-link>
        <router-link
          v-if="authStore.isAdmin"
          to="/admin"
          class="nav-link"
          :class="{ 'nav-link-active': route.name === 'Admin' }"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Admin
        </router-link>
      </div>

      <!-- Right actions -->
      <div class="flex items-center gap-3">
        <!-- Authenticated user menu -->
        <template v-if="authStore.isAuthenticated">
          <div class="relative" ref="userMenuRef">
            <button
              @click="userMenuOpen = !userMenuOpen"
              class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 hover:border-violet-500/50 transition-colors"
            >
              <div class="w-6 h-6 rounded-full bg-violet-600 flex items-center justify-center text-white text-xs font-semibold">
                {{ userInitial }}
              </div>
              <span class="text-slate-200 text-sm">{{ authStore.user?.name || authStore.user?.email?.split('@')[0] }}</span>
              <svg class="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <div
              v-if="userMenuOpen"
              class="absolute right-0 top-full mt-2 w-48 bg-slate-800 border border-slate-700 rounded-xl shadow-xl overflow-hidden z-50"
            >
              <div class="px-4 py-3 border-b border-slate-700">
                <p class="text-xs text-slate-400">Signed in as</p>
                <p class="text-sm text-white font-medium truncate">{{ authStore.user?.email }}</p>
                <span class="inline-block mt-1 text-xs px-2 py-0.5 rounded-full"
                  :class="authStore.isAdmin ? 'bg-violet-500/20 text-violet-300' : 'bg-cyan-500/20 text-cyan-300'">
                  {{ authStore.user?.role }}
                </span>
              </div>
              <button
                @click="handleLogout"
                class="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Sign out
              </button>
            </div>
          </div>
        </template>

        <!-- Guest actions -->
        <template v-else>
          <router-link
            to="/login"
            class="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            Sign in
          </router-link>
          <router-link
            to="/login?tab=signup"
            class="px-4 py-2 text-sm font-medium bg-violet-600 hover:bg-violet-500 text-white rounded-lg transition-colors"
          >
            Get started
          </router-link>
        </template>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const userMenuOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

const userInitial = computed(() => {
  const name = authStore.user?.name || authStore.user?.email || ''
  return name.charAt(0).toUpperCase()
})

async function handleLogout() {
  await authStore.logout()
  userMenuOpen.value = false
  router.push('/login')
}

function handleClickOutside(event: MouseEvent) {
  if (userMenuRef.value && !userMenuRef.value.contains(event.target as Node)) {
    userMenuOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<style scoped>
.nav-link {
  @apply flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/60 transition-all;
}
.nav-link-active {
  @apply text-white bg-slate-800/80 border border-slate-700/50;
}
</style>
