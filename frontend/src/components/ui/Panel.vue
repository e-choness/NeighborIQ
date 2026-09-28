<script setup lang="ts">
import { cn } from '@/lib/utils'

defineProps<{ title?: string; eyebrow?: string; class?: string }>()
</script>

<template>
  <section :class="cn('rounded-[18px] border border-border bg-surface-2 p-[18px]', $props.class)">
    <header v-if="title || eyebrow || $slots.actions" class="mb-4 flex items-start justify-between gap-4">
      <div>
        <p v-if="eyebrow" class="eyebrow mb-1">{{ eyebrow }}</p>
        <h2 v-if="title" class="text-[15px] font-medium">{{ title }}</h2>
      </div>
      <slot name="actions" />
    </header>
    <slot />
  </section>
</template>
