<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{ tone?: 'neutral' | 'accent' | 'good' | 'warn' | 'bad'; class?: string }>()
const tones = {
  neutral: 'bg-surface-2 text-text-2 border-border',
  accent: 'bg-accent-soft text-accent border-transparent',
  good: 'bg-good/10 text-good border-transparent',
  warn: 'bg-warn/10 text-warn border-transparent',
  bad: 'bg-bad/10 text-bad border-transparent',
}
</script>

<template>
  <span :class="cn('inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium', tones[tone ?? 'neutral'], $props.class)">
    <slot />
  </span>
</template>
