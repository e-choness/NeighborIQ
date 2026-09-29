<script setup lang="ts">
/** Slider with a synced numeric input — drag for exploration, type for precision. */
import { SliderRange, SliderRoot, SliderThumb, SliderTrack } from 'reka-ui'
import { computed } from 'vue'

const props = defineProps<{
  label: string
  min: number
  max: number
  step: number
  prefix?: string
  suffix?: string
  hint?: string
}>()
const model = defineModel<number>({ required: true })
const sliderValue = computed({
  get: () => [Math.min(props.max, Math.max(props.min, model.value))],
  set: (v: number[]) => (model.value = v[0]),
})
const id = `f-${Math.random().toString(36).slice(2, 8)}`

function onInput(event: Event) {
  const value = Number((event.target as HTMLInputElement).value)
  if (Number.isFinite(value)) model.value = value
}
</script>

<template>
  <div class="min-w-0">
    <div class="mb-1.5 flex items-baseline justify-between gap-2">
      <label :for="id" class="truncate text-xs text-text-2">{{ label }}</label>
      <div class="flex shrink-0 items-center gap-0.5 rounded-md border border-transparent px-1 focus-within:border-accent hover:border-border">
        <span v-if="prefix" class="num text-xs text-muted">{{ prefix }}</span>
        <input
          :id="id"
          type="number"
          :value="model"
          :step="step"
          class="num w-[4.5rem] bg-transparent text-right text-xs text-text outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
          @change="onInput"
        />
        <span v-if="suffix" class="whitespace-nowrap text-[11px] text-muted">{{ suffix }}</span>
      </div>
    </div>
    <SliderRoot v-model="sliderValue" :min="min" :max="max" :step="step" class="relative flex h-4 touch-none select-none items-center" :aria-label="label">
      <SliderTrack class="relative h-1 grow rounded-full bg-bar">
        <SliderRange class="absolute h-full rounded-full bg-accent" />
      </SliderTrack>
      <SliderThumb :aria-label="label" class="block h-3.5 w-3.5 rounded-full border-2 border-accent bg-surface shadow focus-visible:outline-2" />
    </SliderRoot>
    <p v-if="hint" class="mt-1.5 text-[11px] leading-snug text-muted">{{ hint }}</p>
  </div>
</template>
