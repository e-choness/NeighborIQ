<script setup lang="ts" generic="T extends string">
import { ToggleGroupItem, ToggleGroupRoot } from 'reka-ui'
import { cn } from '@/lib/utils'

defineProps<{ options: { value: T; label: string }[]; label: string; class?: string; itemClass?: string }>()
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
    :class="cn('inline-flex flex-wrap rounded-xl border border-border bg-surface-2 p-[3px]', $props.class)"
    @update:model-value="update"
  >
    <ToggleGroupItem
      v-for="o in options"
      :key="o.value"
      :value="o.value"
      :class="cn(
        'whitespace-nowrap rounded-[9px] px-[11px] py-1.5 text-xs font-medium text-text-2 transition-colors hover:text-text data-[state=on]:bg-seg-on data-[state=on]:text-text data-[state=on]:shadow-[inset_0_1px_0_var(--glass-hi),0_1px_3px_rgb(0_0_0/0.2)]',
        itemClass,
      )"
    >
      {{ o.label }}
    </ToggleGroupItem>
  </ToggleGroupRoot>
</template>
