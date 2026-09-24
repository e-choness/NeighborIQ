<script setup lang="ts">
import { LogOut, Moon, Sun } from '@lucide/vue'
import { RouterLink, useRouter } from 'vue-router'
import Button from '@/components/ui/Button.vue'
import { theme, toggleTheme } from '@/lib/theme'
import { useAuth } from '@/stores/auth'

defineProps<{ overlay?: boolean }>()
const auth = useAuth()
const router = useRouter()

const links = [
  { to: '/', label: 'Map' },
  { to: '/explore', label: 'Explore' },
  { to: '/analyze', label: 'Analyze' },
  { to: '/portfolio', label: 'Portfolio' },
]

async function signOut() {
  await auth.logout()
  router.push('/')
}
</script>

<template>
  <header class="fixed inset-x-0 top-0 z-40 px-3 pt-3 sm:px-4">
    <nav
      class="glass mx-auto flex h-12 items-center gap-1 rounded-xl px-2 sm:gap-2 sm:px-3"
      :class="overlay ? 'max-w-none' : 'max-w-6xl'"
      aria-label="Primary"
    >
      <RouterLink to="/" class="mr-1 flex shrink-0 items-center gap-2 rounded-md px-1.5 py-1 sm:mr-3" aria-label="NeighborIQ home">
        <svg viewBox="0 0 24 24" class="h-5 w-5 text-accent" aria-hidden="true">
          <path fill="currentColor" d="M12 2 21 7.2v9.6L12 22l-9-5.2V7.2L12 2Zm0 3.5L6 9v6l6 3.5 6-3.5V9l-6-3.5Z" />
          <path fill="currentColor" d="M12 9.2 14.4 10.6v2.8L12 14.8l-2.4-1.4v-2.8L12 9.2Z" />
        </svg>
        <span class="hidden text-sm font-semibold tracking-tight sm:inline">NeighborIQ</span>
      </RouterLink>
      <div class="flex min-w-0 flex-1 items-center gap-0.5 overflow-x-auto [scrollbar-width:none] sm:gap-1">
      <RouterLink
        v-for="l in links"
        :key="l.to"
        :to="l.to"
        class="shrink-0 rounded-md px-2 py-1.5 text-[13px] text-text-2 transition-colors hover:text-text sm:px-2.5"
        active-class="!text-text bg-surface-2"
        :exact-active-class="l.to === '/' ? '!text-text bg-surface-2' : undefined"
      >
        {{ l.label }}
      </RouterLink>
      <RouterLink v-if="auth.isAdmin" to="/admin" class="shrink-0 rounded-md px-2 py-1.5 text-[13px] text-text-2 hover:text-text" active-class="!text-text bg-surface-2">
        Admin
      </RouterLink>
      </div>

      <div class="flex shrink-0 items-center gap-1">
        <Button variant="ghost" size="icon" :aria-label="theme === 'dark' ? 'Use light theme' : 'Use dark theme'" @click="toggleTheme">
          <Sun v-if="theme === 'dark'" class="h-4 w-4" />
          <Moon v-else class="h-4 w-4" />
        </Button>
        <template v-if="auth.isAuthenticated">
          <span class="hidden max-w-40 truncate text-xs text-muted md:inline">{{ auth.user?.email }}</span>
          <Button variant="ghost" size="icon" aria-label="Sign out" @click="signOut"><LogOut class="h-4 w-4" /></Button>
        </template>
        <Button v-else to="/login" variant="secondary" size="sm">Sign in</Button>
      </div>
    </nav>
  </header>
</template>
