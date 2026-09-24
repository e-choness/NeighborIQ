<script setup lang="ts">
/** Product screenshots with a tab per page of the app. */
import { ref } from 'vue'
import analyze from '../../../images/analyze.png'
import explore from '../../../images/explore.png'
import home from '../../../images/home.png'
import listing from '../../../images/listing.png'

const SHOTS = [
  { key: 'Home', src: home, alt: '3D hexagon map of gross rental yield across Toronto with city medians and the highest-yield listings', caption: 'Home — a city at a glance: yield, $/sq ft or price cuts as a 3D hexagon map.' },
  { key: 'Listing', src: listing, alt: 'Listing page with fair value against comparable listings, a cash-flow panel and price history', caption: 'Listing — fair value with its comparables on a map, and a cash flow you can edit.' },
  { key: 'Analyze', src: analyze, alt: 'Deal analyzer for a property found elsewhere, in light mode', caption: 'Analyze — the same analysis for any property, pre-filled from the assessment roll where available.' },
  { key: 'Explore', src: explore, alt: 'Explore page with filters above a map and list of listings', caption: 'Explore — filter by yield, price cut, type and size; map and list stay in sync.' },
]
const current = ref(0)
</script>

<template>
  <section class="screens">
    <div class="tabs" role="tablist" aria-label="App screens">
      <button v-for="(s, i) in SHOTS" :id="`tab-${s.key}`" :key="s.key" role="tab" type="button" :aria-selected="current === i" :aria-controls="`panel-${s.key}`" @click="current = i">
        {{ s.key }}
      </button>
    </div>
    <figure v-for="(s, i) in SHOTS" v-show="current === i" :id="`panel-${s.key}`" :key="s.key" role="tabpanel" :aria-labelledby="`tab-${s.key}`">
      <img :src="s.src" :alt="s.alt" loading="lazy" />
      <figcaption>{{ s.caption }}</figcaption>
    </figure>
  </section>
</template>

<style scoped>
.screens {
  max-width: 1152px;
  margin: 48px auto 0;
  padding: 0 24px;
}
.tabs {
  display: flex;
  gap: 4px;
  justify-content: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.tabs button {
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 14px;
  color: var(--vp-c-text-2);
  border: 1px solid transparent;
}
.tabs button[aria-selected='true'] {
  color: var(--vp-c-brand-1);
  border-color: var(--vp-c-brand-1);
}
.tabs button:focus-visible {
  outline: 2px solid var(--vp-c-brand-1);
  outline-offset: 2px;
}
figure {
  margin: 0;
}
img {
  width: 100%;
  border-radius: 14px;
  border: 1px solid var(--vp-c-divider);
  box-shadow: 0 24px 60px -24px rgb(0 0 0 / 0.45);
}
figcaption {
  text-align: center;
  color: var(--vp-c-text-2);
  font-size: 14px;
  margin-top: 12px;
}
</style>
