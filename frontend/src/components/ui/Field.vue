<script setup lang="ts">
defineProps<{ label: string; for?: string; hint?: string }>()
</script>

<template>
  <div>
    <label :for="$props.for" class="mb-1.5 block text-xs text-text-2">{{ label }}</label>
    <slot />
    <p v-if="hint" class="mt-1 text-[11px] text-muted">{{ hint }}</p>
  </div>
</template>
