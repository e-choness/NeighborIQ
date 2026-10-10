declare module '*.png' {
  const src: string
  export default src
}
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent
  export default component
}
declare module 'virtual:mermaid-config' {
  const config: Record<string, unknown>
  export default config
}
