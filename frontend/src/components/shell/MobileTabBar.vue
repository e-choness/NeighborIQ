<script setup lang="ts">
/** Phone navigation (<1024px): a floating glass tab bar above the home indicator. */
import { RouterLink } from 'vue-router'
import { NAV, useActiveNav } from './nav'

const active = useActiveNav()
</script>

<template>
  <nav
    aria-label="Primary"
    class="glass absolute inset-x-3 bottom-[max(env(safe-area-inset-bottom),18px)] z-25 grid h-[66px] grid-cols-5 items-center rounded-[22px]"
  >
    <RouterLink
      v-for="(n, i) in NAV"
      :key="n.to"
      :to="n.to"
      :aria-current="i === active ? 'page' : undefined"
      class="flex h-full flex-col items-center justify-center gap-[3px]"
      :class="i === active ? 'text-accent' : 'text-muted'"
    >
      <component :is="n.icon" class="h-5 w-5" :stroke-width="1.75" aria-hidden="true" />
      <span class="text-[10px]">{{ n.short }}</span>
    </RouterLink>
  </nav>
</template>
