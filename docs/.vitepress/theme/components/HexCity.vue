<script setup lang="ts">
/**
 * Home-page hero: the app's 3D hexagon map in miniature. Each cell's height and
 * colour show the same value (as in the app); the blue point is a subject listing
 * with its comparable-search rings. Decorative — the real numbers are in the docs.
 */
import { useData } from 'vitepress'
import { computed } from 'vue'
import { hexCity, prismColors, SURFACE } from '../lib/hexcity.js'

const { isDark } = useData()
const mode = computed(() => (isDark.value ? 'dark' : 'light'))

const W = 520
const H = 400
const prisms = hexCity({ cx: 262, cy: 236, rx: 236, r: 13, maxH: 112, seed: 11 })
const minX = Math.min(...prisms.map((p) => p.x))
const maxX = Math.max(...prisms.map((p) => p.x))
const subject = prisms.filter((p) => p.rim < 0.35).reduce((best, p) => (p.t > best.t ? p : best))

const cells = computed(() =>
  prisms.map((p) => ({
    ...p,
    c: prismColors(p.t, mode.value),
    style: {
      '--d': `${(0.1 + ((p.x - minX) / (maxX - minX)) * 0.8 + p.rim * 0.2).toFixed(2)}s`,
      '--h': `${p.h.toFixed(1)}px`,
      opacity: p.rim > 0.6 ? 1 - (p.rim - 0.6) * 1.4 : 1,
    },
  })),
)
const subjectColor = computed(() => SURFACE[mode.value].subject)
const bg = computed(() => SURFACE[mode.value].bg)
</script>

<template>
  <figure class="hex-city" aria-hidden="true">
    <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="xMidYMid meet">
      <g v-for="p in cells" :key="p.id" class="p" :style="p.style">
        <g class="lift">
          <g class="s">
            <path :d="p.left" :fill="p.c.left" />
            <path :d="p.front" :fill="p.c.front" />
            <path :d="p.right" :fill="p.c.right" />
          </g>
          <path class="t" :d="p.top" :fill="p.c.top" :stroke="p.c.edge" stroke-width="0.6" />
        </g>
      </g>
      <g :transform="`translate(${subject.x} ${subject.y - subject.h})`">
        <ellipse v-for="k in 3" :key="k" class="ring" :class="`r${k}`" :rx="30 * k" :ry="15.6 * k" fill="none" :stroke="subjectColor" stroke-width="1.2" />
        <circle class="dot" r="5" :fill="subjectColor" :stroke="bg" stroke-width="2" />
      </g>
    </svg>
  </figure>
</template>

<style scoped>
.hex-city {
  margin: 0;
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
}
svg {
  width: 100%;
  height: auto;
  max-height: 100%;
  overflow: visible;
}
.p .s {
  transform-box: fill-box;
  transform-origin: 50% 100%;
  animation: grow 1.5s cubic-bezier(0.2, 0.8, 0.2, 1) var(--d) both;
}
.p .t {
  animation: lift 1.5s cubic-bezier(0.2, 0.8, 0.2, 1) var(--d) both;
}
.p .lift {
  transition: transform 0.25s ease, filter 0.25s ease;
}
.p:hover .lift {
  transform: translateY(-8px);
  filter: brightness(1.25);
}
@keyframes grow {
  from {
    transform: scaleY(0);
  }
}
@keyframes lift {
  from {
    transform: translateY(var(--h));
  }
}
.ring {
  transform-box: fill-box;
  transform-origin: 50% 50%;
  opacity: 0;
  animation: ring 4.5s ease-out 1.6s infinite;
  pointer-events: none;
}
.r2 {
  animation-delay: 2.1s;
}
.r3 {
  animation-delay: 2.6s;
}
@keyframes ring {
  0% {
    opacity: 0;
    transform: scale(0.35);
  }
  20% {
    opacity: 0.9;
  }
  100% {
    opacity: 0;
    transform: scale(1);
  }
}
.dot {
  animation: pop 0.5s ease-out 1.4s both;
  pointer-events: none;
}
@keyframes pop {
  from {
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .p .s,
  .p .t,
  .ring,
  .dot {
    animation: none;
  }
  .ring {
    opacity: 0.5;
  }
  .p .lift {
    transition: none;
  }
}
</style>
