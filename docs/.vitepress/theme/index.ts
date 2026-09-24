import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import { h } from 'vue'
import '@fontsource-variable/geist'
import '@fontsource-variable/geist-mono'
import './custom.css'
import ApiReference from './components/ApiReference.vue'
import CashFlowCalculator from './components/CashFlowCalculator.vue'
import HexCity from './components/HexCity.vue'
import Screens from './components/Screens.vue'

export default {
  extends: DefaultTheme,
  Layout: () => h(DefaultTheme.Layout, null, { 'home-hero-image': () => h(HexCity) }),
  enhanceApp({ app }) {
    app.component('ApiReference', ApiReference)
    app.component('CashFlowCalculator', CashFlowCalculator)
    app.component('Screens', Screens)
  },
} satisfies Theme
