<script setup lang="ts">
/** The app on the docs home: a walkthrough video, then a tab per screen. */
import { withBase } from 'vitepress'
import { ref } from 'vue'

const media = (file: string) => withBase(`/media/${file}`)
const home = media('home.png')
const explore = media('explore.png')
const listing = media('listing.png')
const analyze = media('analyze.png')
const homePhone = media('home-phone.png')
const listingPhone = media('listing-phone.png')

type Shot = { key: string; caption: string } & ({ video: string; poster: string } | { src: string; alt: string } | { phones: { src: string; alt: string }[] })

const SHOTS: Shot[] = [
  { key: 'Walkthrough', video: media('walkthrough.mp4'), poster: home, caption: 'A 50-second tour on the demo data: Map → Explore → Listing → Analyze → light theme.' },
  { key: 'Map', src: home, alt: '3D hexagon columns of gross rental yield across Toronto, with city medians and the best-yield listings', caption: 'Map — a city at a glance: yield, $/sq ft, price cuts or days listed, per ~0.7 km² column.' },
  { key: 'Explore', src: explore, alt: 'Filters and a list of listings beside the same listings as dots on the map', caption: 'Explore — filter by type, size, price and price cuts; the list and the map stay in sync.' },
  { key: 'Listing', src: listing, alt: 'A listing with its asking price against comparable listings, and the comparables on the map', caption: 'Listing — fair value, cash flow, history and area in tabs, with the comparables on the map.' },
  { key: 'Analyze', src: analyze, alt: 'A property’s inputs and its result beside the map of nearby comparables', caption: 'Analyze — the same analysis for any address or neighbourhood, result pinned beside the map.' },
  {
    key: 'Phone',
    phones: [
      { src: homePhone, alt: 'The map screen on a phone, with a bottom sheet and tab bar' },
      { src: listingPhone, alt: 'A listing on a phone' },
    ],
    caption: 'On phones the panels become a bottom sheet over the map, with a tab bar.',
  },
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
      <video v-if="'video' in s" :src="s.video" :poster="s.poster" autoplay muted loop playsinline controls preload="metadata" aria-label="Walkthrough of the app" />
      <div v-else-if="'phones' in s" class="phones">
        <img v-for="p in s.phones" :key="p.src" :src="p.src" :alt="p.alt" loading="lazy" />
      </div>
      <img v-else :src="s.src" :alt="s.alt" loading="lazy" />
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
  width: fit-content;
  max-width: 100%;
  flex-wrap: wrap;
  gap: 2px;
  padding: 3px;
  margin: 0 auto 16px;
  border-radius: 12px;
  border: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-soft);
}
.tabs button {
  padding: 6px 12px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 500;
  color: var(--vp-c-text-2);
  white-space: nowrap;
}
.tabs button:hover {
  color: var(--vp-c-text-1);
}
.tabs button[aria-selected='true'] {
  color: var(--vp-c-text-1);
  background: var(--niq-glass);
  box-shadow: inset 0 1px 0 var(--niq-glass-hi), 0 1px 3px rgb(0 0 0 / 0.2);
}
.tabs button:focus-visible {
  outline: 2px solid var(--vp-c-brand-1);
  outline-offset: 2px;
}
figure {
  margin: 0;
}
img,
video {
  display: block;
  width: 100%;
  border-radius: 18px;
  border: 1px solid var(--niq-glass-edge);
  box-shadow: inset 0 1px 0 var(--niq-glass-hi), var(--niq-shadow);
}
.phones {
  display: flex;
  justify-content: center;
  gap: 24px;
}
.phones img {
  width: min(300px, 44%);
}
figcaption {
  text-align: center;
  color: var(--vp-c-text-2);
  font-size: 14px;
  margin-top: 12px;
}
</style>
