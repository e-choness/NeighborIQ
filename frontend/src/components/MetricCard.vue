<template>
  <div
    class="bg-slate-800/60 border rounded-xl p-3 flex flex-col gap-1.5"
    :class="borderClass"
  >
    <div class="flex items-center gap-1.5">
      <div class="w-5 h-5 rounded flex items-center justify-center" :class="iconBgClass">
        <!-- Chart bar icon -->
        <svg v-if="icon === 'chart-bar'" class="w-3 h-3" :class="iconColorClass" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <!-- Trending up icon -->
        <svg v-else-if="icon === 'trending-up'" class="w-3 h-3" :class="iconColorClass" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
        <!-- Default icon -->
        <svg v-else class="w-3 h-3" :class="iconColorClass" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <span class="text-xs text-slate-400">{{ label }}</span>
    </div>
    <p class="text-lg font-bold" :class="valueColorClass">{{ value }}</p>
    <p v-if="sub" class="text-xs text-slate-500">{{ sub }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  label: string
  value: string
  sub?: string
  color: 'violet' | 'emerald' | 'cyan' | 'amber'
  icon: string
}>()

const borderClass = computed(() => ({
  'border-violet-500/20': props.color === 'violet',
  'border-emerald-500/20': props.color === 'emerald',
  'border-cyan-500/20': props.color === 'cyan',
  'border-amber-500/20': props.color === 'amber',
}))

const iconBgClass = computed(() => ({
  'bg-violet-500/20': props.color === 'violet',
  'bg-emerald-500/20': props.color === 'emerald',
  'bg-cyan-500/20': props.color === 'cyan',
  'bg-amber-500/20': props.color === 'amber',
}))

const iconColorClass = computed(() => ({
  'text-violet-400': props.color === 'violet',
  'text-emerald-400': props.color === 'emerald',
  'text-cyan-400': props.color === 'cyan',
  'text-amber-400': props.color === 'amber',
}))

const valueColorClass = computed(() => ({
  'text-violet-300': props.color === 'violet',
  'text-emerald-300': props.color === 'emerald',
  'text-cyan-300': props.color === 'cyan',
  'text-amber-300': props.color === 'amber',
}))
</script>
