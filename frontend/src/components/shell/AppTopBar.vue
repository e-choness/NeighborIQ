<script setup lang="ts">
/** Glass top bar: wordmark, city, demo-data flag and the account. */
import { LogOut, Moon, Sun } from '@lucide/vue'
import { DropdownMenuContent, DropdownMenuItem, DropdownMenuPortal, DropdownMenuRoot, DropdownMenuTrigger } from 'reka-ui'
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { theme, toggleTheme } from '@/lib/theme'
import { isPhone } from '@/lib/viewport'
import { useAuth } from '@/stores/auth'
import { useCity } from '@/stores/city'

const auth = useAuth()
const cities = useCity()
const router = useRouter()

const initials = computed(() => {
  const u = auth.user
  if (!u) return ''
  const source = u.name?.trim() || u.email.split('@')[0]
  const parts = source.split(/[\s._-]+/).filter(Boolean)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? parts[0]?.[1] ?? '')).toUpperCase()
})

async function signOut() {
  await auth.logout()
  router.push('/')
}
</script>

<template>
  <header
    class="glass absolute z-20 flex items-center"
    :class="isPhone
      ? 'inset-x-3 top-[max(env(safe-area-inset-top),12px)] h-[50px] gap-2 rounded-2xl pl-3.5 pr-2'
      : 'left-[88px] right-3 top-3 h-[52px] gap-3.5 rounded-[18px] pl-[18px] pr-2.5'"
  >
    <RouterLink to="/" class="font-display whitespace-nowrap text-[23px] tracking-[0.04em] text-text hover:no-underline">NeighborIQ</RouterLink>

    <template v-if="!isPhone && cities.markets?.length">
      <div class="h-[22px] w-px bg-border" />
      <div role="tablist" aria-label="City" class="flex min-w-0 gap-0.5 overflow-x-auto [scrollbar-width:none]">
        <button
          v-for="m in cities.markets"
          :key="m.city"
          role="tab"
          :aria-selected="m.city === cities.city"
          class="whitespace-nowrap rounded-[9px] px-2.5 py-1.5 text-[13px] font-medium transition-colors"
          :class="m.city === cities.city
            ? 'bg-seg-on text-text shadow-[inset_0_1px_0_var(--glass-hi),0_1px_3px_rgb(0_0_0/0.2)]'
            : 'text-text-2 hover:text-text'"
          @click="cities.select(m.city)"
        >
          {{ m.city }}
        </button>
      </div>
    </template>

    <div class="flex-1" />

    <template v-if="isPhone">
      <select
        v-if="cities.markets?.length"
        :value="cities.city"
        aria-label="City"
        class="h-[34px] min-w-0 rounded-[10px] border border-border bg-field px-2 text-[13px] text-text"
        @change="cities.select(($event.target as HTMLSelectElement).value)"
      >
        <option v-for="m in cities.markets" :key="m.city" :value="m.city">{{ m.city }}</option>
      </select>
      <button
        type="button"
        :aria-label="theme === 'dark' ? 'Use light theme' : 'Use dark theme'"
        class="grid h-[34px] w-[34px] shrink-0 place-items-center rounded-[10px] text-text-2"
        @click="toggleTheme"
      >
        <Sun v-if="theme === 'dark'" class="h-[18px] w-[18px]" :stroke-width="1.75" />
        <Moon v-else class="h-[18px] w-[18px]" :stroke-width="1.75" />
      </button>
    </template>
    <template v-else>
      <RouterLink
        v-if="cities.market && cities.market.synthetic_share_pct > 0"
        to="/data"
        class="whitespace-nowrap rounded-full border border-border bg-surface-2 px-[9px] py-1 text-[11px] text-warn hover:no-underline"
      >
        Demo data
      </RouterLink>
      <span v-if="auth.user" class="max-w-48 truncate text-xs text-text-2">{{ auth.user.email }}</span>
    </template>

    <DropdownMenuRoot v-if="auth.user">
      <DropdownMenuTrigger
        :aria-label="`Account: ${auth.user.email}`"
        class="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-accent-deep text-[11px] font-semibold text-accent-ink"
      >
        {{ initials }}
      </DropdownMenuTrigger>
      <DropdownMenuPortal>
        <DropdownMenuContent align="end" :side-offset="8" class="glass z-50 min-w-44 rounded-[14px] p-1 text-sm">
          <p v-if="isPhone" class="truncate px-2.5 py-1.5 text-xs text-muted">{{ auth.user.email }}</p>
          <DropdownMenuItem class="flex cursor-pointer items-center gap-2 rounded-[10px] px-2.5 py-2 text-text outline-none data-[highlighted]:bg-seg-on" @select="signOut">
            <LogOut class="h-4 w-4" :stroke-width="1.75" /> Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenuPortal>
    </DropdownMenuRoot>
    <RouterLink
      v-else
      to="/login"
      class="inline-flex h-8 shrink-0 items-center rounded-[10px] border border-border bg-surface-2 px-3 text-xs font-medium text-text hover:no-underline"
    >
      Sign in
    </RouterLink>
  </header>
</template>
