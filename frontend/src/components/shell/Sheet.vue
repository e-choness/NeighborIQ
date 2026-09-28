<script setup lang="ts">
/**
 * A docked glass panel over the map. Desktop: left (400px), right (480px) or centre (with the
 * map dimmed behind). Phones: a bottom sheet with three snaps; the map stays interactive
 * behind `peek` and `half`. `header` doesn't scroll; the default slot does.
 */
import { onBeforeUnmount, onMounted } from 'vue'
import { prefersReducedMotion } from '@/lib/theme'
import { isPhone } from '@/lib/viewport'
import { useShell } from '@/stores/shell'

const props = withDefaults(
  defineProps<{
    side?: 'left' | 'right' | 'center'
    label: string
    /** Left sheet grows with its content instead of reaching the bottom (Home). */
    fit?: boolean
    /** Scroll area padding classes. */
    bodyClass?: string
  }>(),
  { side: 'left', fit: false, bodyClass: '' },
)

const shell = useShell()
const still = prefersReducedMotion()

const desktop = {
  left: 'left-[88px] top-[76px] w-[400px]',
  right: 'right-3 top-[76px] bottom-3 w-[480px]',
  center: 'left-[88px] right-3 top-[76px] bottom-3',
}

// A vertical drag of more than 30px on the grabber moves one snap; a tap cycles.
let startY: number | null = null
let dragged = false
function onPointerDown(e: PointerEvent) {
  startY = e.clientY
  dragged = false
  window.addEventListener('pointerup', onPointerUp, { once: true })
}
function onPointerUp(e: PointerEvent) {
  if (startY === null) return
  const dy = e.clientY - startY
  startY = null
  if (Math.abs(dy) < 30) return
  dragged = true
  shell.step(dy < 0 ? 1 : -1)
}
function onGrabberClick() {
  if (dragged) {
    dragged = false
    return
  }
  shell.cycle()
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && isPhone.value && shell.snap !== 'peek') shell.snap = 'peek'
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('pointerup', onPointerUp)
})
</script>

<template>
  <section
    :aria-label="label"
    class="glass absolute z-15 flex flex-col overflow-hidden text-text"
    :class="isPhone
      ? ['inset-x-0 bottom-0 rounded-t-[28px] border-b-0', still ? '' : 'transition-[height] duration-[350ms] ease-[cubic-bezier(.2,.8,.2,1)]']
      : ['rounded-[22px]', desktop[side], side === 'left' ? (fit ? 'max-h-[calc(100%-88px)]' : 'bottom-3') : '']"
    :style="isPhone ? { height: `${shell.sheetHeight}px` } : undefined"
  >
    <button
      v-if="isPhone"
      type="button"
      aria-label="Resize panel"
      class="grid h-[26px] shrink-0 cursor-grab touch-none place-items-center"
      @pointerdown="onPointerDown"
      @click="onGrabberClick"
    >
      <span class="h-[5px] w-10 rounded-[9px] bg-bar" />
    </button>
    <slot name="header" />
    <div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden" :class="props.bodyClass">
      <slot />
      <div v-if="isPhone" class="h-24 pb-[env(safe-area-inset-bottom)]" aria-hidden="true" />
    </div>
  </section>
</template>
