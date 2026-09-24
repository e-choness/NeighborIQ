<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{ title?: string; eyebrow?: string; class?: string }>()
</script>

<template>
  <section :class="cn('rounded-2xl border border-border bg-surface p-5', $props.class)">
    <header v-if="title || eyebrow || $slots.actions" class="mb-4 flex items-start justify-between gap-4">
      <div>
        <p v-if="eyebrow" class="eyebrow mb-1">{{ eyebrow }}</p>
        <h2 v-if="title" class="text-base font-semibold tracking-tight">{{ title }}</h2>
      </div>
      <slot name="actions" />
    </header>
    <slot />
  </section>
</template>
