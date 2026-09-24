<script setup lang="ts" generic="T extends string">
import { ToggleGroupItem, ToggleGroupRoot } from 'reka-ui'

defineProps<{ options: { value: T; label: string }[]; label: string }>()
const model = defineModel<T>({ required: true })

function update(value: unknown) {
  if (typeof value === 'string' && value) model.value = value as T
}
</script>

<template>
  <ToggleGroupRoot
    :model-value="model"
    type="single"
    :aria-label="label"
    class="inline-flex rounded-lg border border-border bg-surface-2 p-0.5"
    @update:model-value="update"
  >
    <ToggleGroupItem
      v-for="o in options"
      :key="o.value"
      :value="o.value"
      class="rounded-md px-3 py-1.5 text-xs font-medium text-text-2 transition-colors hover:text-text data-[state=on]:bg-surface data-[state=on]:text-text data-[state=on]:shadow-sm"
    >
      {{ o.label }}
    </ToggleGroupItem>
  </ToggleGroupRoot>
</template>
