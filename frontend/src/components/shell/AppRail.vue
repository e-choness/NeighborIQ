<script setup lang="ts">
/** Desktop navigation (≥1024px): a floating glass rail on the left edge. */
import { Moon, Sun } from '@lucide/vue'
import { RouterLink } from 'vue-router'
import { theme, toggleTheme } from '@/lib/theme'
import { NAV, useActiveNav } from './nav'

const active = useActiveNav()
</script>

<template>
  <nav
    aria-label="Primary"
    class="glass absolute bottom-3 left-3 top-3 z-20 flex w-16 flex-col items-center rounded-[22px] py-3.5"
  >
    <RouterLink to="/" aria-label="NeighborIQ home" title="NeighborIQ home" class="grid h-10 w-10 place-items-center text-accent">
      <svg viewBox="0 0 24 24" class="h-6 w-6" aria-hidden="true">
        <path fill="currentColor" d="M12 2 21 7.2v9.6L12 22l-9-5.2V7.2L12 2Zm0 3.5L6 9v6l6 3.5 6-3.5V9l-6-3.5Z" />
        <path fill="currentColor" d="M12 9.2 14.4 10.6v2.8L12 14.8l-2.4-1.4v-2.8L12 9.2Z" />
      </svg>
    </RouterLink>
    <div class="my-3.5 h-px w-6 bg-border" />
    <div class="flex flex-1 flex-col items-center gap-2.5">
      <RouterLink
        v-for="(n, i) in NAV"
        :key="n.to"
        :to="n.to"
        :aria-label="n.label"
        :title="n.label"
        :aria-current="i === active ? 'page' : undefined"
        class="grid h-11 w-11 place-items-center rounded-full border transition-colors"
        :class="i === active
          ? 'border-border-strong bg-seg-on text-text shadow-[inset_0_1px_0_var(--glass-hi)]'
          : 'border-transparent text-muted hover:text-text-2'"
      >
        <component :is="n.icon" class="h-5 w-5" :stroke-width="1.75" aria-hidden="true" />
      </RouterLink>
    </div>
    <div class="num mb-2.5 text-[11px] text-muted" aria-hidden="true">0{{ active + 1 }}</div>
    <button
      type="button"
      :aria-label="theme === 'dark' ? 'Use light theme' : 'Use dark theme'"
      :title="theme === 'dark' ? 'Use light theme' : 'Use dark theme'"
      class="grid h-10 w-10 place-items-center rounded-full border border-border bg-surface-2 text-text-2 hover:text-text"
      @click="toggleTheme"
    >
      <Sun v-if="theme === 'dark'" class="h-[18px] w-[18px]" :stroke-width="1.75" />
      <Moon v-else class="h-[18px] w-[18px]" :stroke-width="1.75" />
    </button>
  </nav>
</template>
