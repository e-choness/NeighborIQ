<script setup lang="ts">
import { Info } from '@lucide/vue'
import { TooltipContent, TooltipPortal, TooltipProvider, TooltipRoot, TooltipTrigger } from 'reka-ui'

defineProps<{ text: string }>()
</script>

<template>
  <TooltipProvider :delay-duration="150">
    <TooltipRoot>
      <TooltipTrigger class="inline-flex text-muted hover:text-text-2" :aria-label="text">
        <Info class="h-3.5 w-3.5" />
      </TooltipTrigger>
      <TooltipPortal>
        <TooltipContent side="top" :side-offset="6" class="z-50 max-w-72 rounded-lg border border-border bg-surface px-3 py-2 text-xs leading-relaxed text-text-2 shadow-xl">
          {{ text }}
        </TooltipContent>
      </TooltipPortal>
    </TooltipRoot>
  </TooltipProvider>
</template>
