<template>
  <div :class="props.class" v-html="svg"></div>
</template>

<script setup lang="ts">
/**
 * Replaces vitepress-plugin-mermaid's component (aliased in config.mts). The plugin's
 * version hard-codes theme 'dark' in dark mode and leaves Mermaid's startOnLoad on
 * until after two awaits, so empty .mermaid divs flash "Syntax error in text".
 */
import { onMounted, onUnmounted, ref } from 'vue'
import { useData } from 'vitepress'
import settings from 'virtual:mermaid-config'

const props = defineProps({
  graph: { type: String, required: true },
  id: { type: String, required: true },
  class: { type: String, default: 'mermaid' },
})

const { frontmatter } = useData()
const svg = ref('')
let observer: MutationObserver | undefined

// darkTheme is our own key; Mermaid doesn't know it
const { darkTheme = 'redux-dark-color', ...config } = settings as Record<string, any>

async function renderChart(mermaid: typeof import('mermaid').default) {
  const dark = document.documentElement.classList.contains('dark')
  const theme = dark ? darkTheme : (frontmatter.value.mermaidTheme ?? config.theme)
  mermaid.initialize({ ...config, startOnLoad: false, theme })
  const { svg: code } = await mermaid.render(props.id, decodeURIComponent(props.graph))
  // Mermaid removes its render target behind Vue's back; the salt forces v-html to re-apply
  svg.value = `${code}<span hidden>${Math.random().toString(36).slice(2)}</span>`
}

onMounted(async () => {
  const mermaid = (await import('mermaid')).default
  // Before any other await: startOnLoad would otherwise render the still-empty divs on window load
  mermaid.initialize({ startOnLoad: false })
  let dark = document.documentElement.classList.contains('dark')
  observer = new MutationObserver(() => {
    const now = document.documentElement.classList.contains('dark')
    if (now !== dark) {
      dark = now
      renderChart(mermaid)
    }
  })
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  await renderChart(mermaid)
})

onUnmounted(() => observer?.disconnect())
</script>
