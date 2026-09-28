<script setup lang="ts">
/**
 * Map-first shell: one persistent map behind every primary route, with navigation, the top bar
 * and each page's docked sheet floating over it. Only the sheets scroll.
 */
import { computed, defineAsyncComponent, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppRail from '@/components/shell/AppRail.vue'
import AppTopBar from '@/components/shell/AppTopBar.vue'
import MobileTabBar from '@/components/shell/MobileTabBar.vue'
import { isPhone } from '@/lib/viewport'
import { useShell } from '@/stores/shell'

const MapStage = defineAsyncComponent(() => import('@/components/map/MapStage.vue'))
const route = useRoute()
const shell = useShell()

const isMapLayout = computed(() => route.meta.layout !== 'plain')

// Phones: each screen opens its sheet at the snap that suits it
const DEFAULT_SNAP: Record<string, 'half' | 'full'> = { home: 'half', explore: 'half', listing: 'half', analyze: 'full', portfolio: 'full', data: 'full' }
watch(() => route.name, (name) => (shell.snap = DEFAULT_SNAP[String(name)] ?? 'half'), { immediate: true })
</script>

<template>
  <a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">Skip to content</a>

  <div v-if="isMapLayout" class="fixed inset-0 overflow-hidden">
    <!-- DOM order = tab order: navigation, top bar, sheet, then the map canvas -->
    <MobileTabBar v-if="isPhone" />
    <AppRail v-else />
    <AppTopBar />
    <main id="main" class="contents">
      <RouterView />
    </main>
    <div
      v-if="shell.toast"
      role="status"
      class="absolute bottom-24 left-1/2 z-40 -translate-x-1/2 whitespace-nowrap rounded-[14px] bg-accent-deep px-4 py-2.5 text-[13px] text-accent-ink shadow-[var(--shadow)]"
    >
      {{ shell.toast }}
    </div>
    <MapStage />
  </div>

  <main v-else id="main" class="min-h-full">
    <RouterView />
  </main>
</template>
