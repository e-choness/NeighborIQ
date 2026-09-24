<script setup lang="ts">
/** A labelled figure. Colour is never the only signal: tone pairs with the sub-label. */
defineProps<{ label: string; value: string; sub?: string; tone?: 'good' | 'bad' | 'neutral'; size?: 'md' | 'lg' }>()
</script>

<template>
  <div class="min-w-0">
    <p class="text-xs text-muted">{{ label }}</p>
    <p
      class="num mt-1 truncate font-medium tracking-tight"
      :class="[size === 'lg' ? 'text-3xl' : 'text-lg', tone === 'good' ? 'text-good' : tone === 'bad' ? 'text-bad' : 'text-text']"
    >
      {{ value }}
    </p>
    <p v-if="sub" class="mt-0.5 truncate text-xs text-text-2">{{ sub }}</p>
  </div>
</template>
