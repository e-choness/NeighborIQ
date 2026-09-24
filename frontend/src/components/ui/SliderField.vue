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
  <div>
    <div class="mb-2 flex items-baseline justify-between gap-3">
      <label :for="id" class="text-xs text-text-2">{{ label }}</label>
      <div class="flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-0.5 focus-within:border-accent">
        <span v-if="prefix" class="text-xs text-muted">{{ prefix }}</span>
        <input
          :id="id"
          type="number"
          :value="model"
          :step="step"
          class="num w-20 bg-transparent text-right text-xs outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
          @change="onInput"
        />
        <span v-if="suffix" class="text-xs text-muted">{{ suffix }}</span>
      </div>
    </div>
    <SliderRoot v-model="sliderValue" :min="min" :max="max" :step="step" class="relative flex h-5 touch-none select-none items-center" :aria-label="label">
      <SliderTrack class="relative h-1 grow rounded-full bg-border-strong">
        <SliderRange class="absolute h-full rounded-full bg-accent" />
      </SliderTrack>
      <SliderThumb class="block h-4 w-4 rounded-full border-2 border-accent bg-surface shadow focus-visible:outline-2" />
    </SliderRoot>
    <p v-if="hint" class="mt-1.5 text-[11px] leading-snug text-muted">{{ hint }}</p>
  </div>
</template>
