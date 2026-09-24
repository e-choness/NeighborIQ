<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import AppFooter from '@/components/AppFooter.vue'

const route = useRoute()
const fullBleed = computed(() => Boolean(route.meta.fullBleed))
</script>

<template>
  <div class="flex min-h-full flex-col">
    <a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">Skip to content</a>
    <AppHeader :overlay="fullBleed" />
    <main id="main" class="flex-1" :class="fullBleed ? '' : 'mx-auto w-full max-w-6xl px-4 pb-16 pt-24 sm:px-6'">
      <RouterView />
    </main>
    <AppFooter v-if="!fullBleed" />
  </div>
</template>
