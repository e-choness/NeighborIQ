<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'
import { computed } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import { cn } from '@/lib/utils'

const button = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-40 select-none',
  {
    variants: {
      variant: {
        primary: 'bg-accent text-accent-ink hover:brightness-110',
        secondary: 'bg-surface-2 text-text hover:bg-border-strong border border-border',
        ghost: 'text-text-2 hover:text-text hover:bg-surface-2',
        outline: 'border border-border-strong text-text hover:bg-surface-2',
        danger: 'text-bad hover:bg-bad/10',
      },
      size: { sm: 'h-8 px-3 text-xs', md: 'h-10 px-4', lg: 'h-12 px-5 text-[15px]', icon: 'h-9 w-9' },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)

type Variants = VariantProps<typeof button>
const props = defineProps<{
  variant?: Variants['variant']
  size?: Variants['size']
  to?: RouteLocationRaw
  type?: 'button' | 'submit'
  class?: string
}>()
const classes = computed(() => cn(button({ variant: props.variant, size: props.size }), props.class))
</script>

<template>
  <RouterLink v-if="to" :to="to" :class="classes"><slot /></RouterLink>
  <button v-else :type="type ?? 'button'" :class="classes"><slot /></button>
</template>
