import { existsSync, statSync } from 'node:fs'
import { dirname, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const REPO = 'https://github.com/e-choness/NeighborIQ'
const BRANCH = 'main'
// GitHub Pages serves project sites under /<repo>/; the Pages workflow passes the exact path
const BASE = process.env.DOCS_BASE ?? '/NeighborIQ/'
const SITE = (process.env.DOCS_SITE_URL ?? 'https://e-choness.github.io') + BASE

const SRC = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const ROOT = resolve(SRC, '..')
// adr/: internal decision records, kept locally and not published
const EXCLUDE = ['scripts/**', 'adr/**', '**/node_modules/**']
const excluded = (abs: string) => {
  const rel = relative(SRC, abs).split(sep).join('/')
  return rel.startsWith('scripts/') || rel.startsWith('adr/')
}

/**
 * The docs are written to read well on GitHub too, so they link to source files with
 * relative paths (../../services/api). Links that leave the docs site are rewritten
 * to GitHub URLs at build time; links between pages are left to VitePress.
 */
function githubLinks(md: any) {
  md.core.ruler.push('github-links', (state: any) => {
    const from = dirname(resolve(SRC, state.env?.relativePath ?? 'index.md'))
    for (const block of state.tokens) {
      for (const token of block.children ?? []) {
        if (token.type !== 'link_open') continue
        const href: string = token.attrGet('href') ?? ''
        if (!href || /^[a-z]+:|^#|^\//i.test(href)) continue
        const [path, hash = ''] = href.split('#')
        const target = resolve(from, decodeURIComponent(path))
        const inSite = target.startsWith(SRC + sep) && !excluded(target)
        if (inSite) continue
        if (!target.startsWith(ROOT + sep) && target !== ROOT) continue
        const isDir = existsSync(target) && statSync(target).isDirectory()
        const rel = relative(ROOT, target).split(sep).join('/')
        token.attrSet('href', `${REPO}/${isDir ? 'tree' : 'blob'}/${BRANCH}/${rel}${hash ? '#' + hash : ''}`)
        token.attrSet('target', '_blank')
        token.attrSet('rel', 'noreferrer')
      }
    }
  })
}

export default withMermaid(
  defineConfig({
    title: 'NeighborIQ',
    description:
      'Rental-property analysis for small investors in Canadian cities: fair value from comparable listings, Canadian cash flow, neighbourhood open data.',
    lang: 'en-CA',
    base: BASE,
    cleanUrls: true,
    lastUpdated: true,
    srcExclude: EXCLUDE,
    // Links to a local instance (http://localhost…) are instructions, not pages
    ignoreDeadLinks: 'localhostLinks',
    head: [
      ['link', { rel: 'icon', type: 'image/svg+xml', href: `${BASE}media/logo.svg` }],
      ['meta', { name: 'theme-color', content: '#090c0b' }],
      ['meta', { property: 'og:type', content: 'website' }],
      ['meta', { property: 'og:title', content: 'NeighborIQ' }],
      [
        'meta',
        {
          property: 'og:description',
          content: 'Is the price fair, will it cash-flow, what is the neighbourhood like — for Canadian rental properties.',
        },
      ],
      ['meta', { property: 'og:image', content: `${SITE}media/og.png` }],
      ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ],
    vite: { build: { chunkSizeWarningLimit: 2000 } }, // mermaid is large and loaded on demand
    markdown: {
      config: githubLinks,
      theme: { light: 'github-light', dark: 'github-dark-dimmed' },
    },
    themeConfig: {
      logo: '/media/logo.svg',
      siteTitle: 'NeighborIQ',
      // One section per reader: people using the app, people running it, people changing it
      nav: [
        { text: 'Guide', link: '/guide/', activeMatch: '^/guide/' },
        { text: 'Self-hosting', link: '/self-hosting/deployment', activeMatch: '^/self-hosting/' },
        { text: 'Development', link: '/development/getting-started', activeMatch: '^/development/' },
        { text: 'Reference', link: '/reference/api', activeMatch: '^/reference/' },
        {
          text: 'More',
          items: [
            { text: 'Changelog', link: '/reference/changelog' },
            { text: 'License', link: '/reference/license' },
            { text: 'Contributing', link: `${REPO}/blob/${BRANCH}/CONTRIBUTING.md` },
            { text: 'Security policy', link: `${REPO}/blob/${BRANCH}/SECURITY.md` },
            { text: 'Issues', link: `${REPO}/issues` },
          ],
        },
      ],
      sidebar: {
        '/guide/': [
          {
            text: 'Using NeighborIQ',
            items: [
              { text: 'Introduction', link: '/guide/' },
              { text: 'Cash-flow calculator', link: '/guide/calculator' },
            ],
          },
          {
            text: 'How it works',
            items: [
              { text: 'Methodology', link: '/guide/methodology' },
              { text: 'Data sources', link: '/guide/data-sources' },
            ],
          },
        ],
        '/self-hosting/': [
          {
            text: 'Self-hosting',
            items: [
              { text: 'Deployment', link: '/self-hosting/deployment' },
              { text: 'Operations', link: '/self-hosting/operations' },
            ],
          },
        ],
        '/development/': [
          {
            text: 'Development',
            items: [
              { text: 'Getting started', link: '/development/getting-started' },
              { text: 'Testing', link: '/development/testing' },
            ],
          },
          {
            text: 'Architecture',
            items: [
              { text: 'Overview', link: '/development/architecture' },
              { text: 'Data model', link: '/development/data-model' },
              { text: 'Frontend', link: '/development/frontend' },
            ],
          },
          {
            text: 'Services',
            items: [
              { text: 'api', link: '/development/services/api' },
              { text: 'ingestion-worker', link: '/development/services/ingestion-worker' },
              { text: 'insights-worker', link: '/development/services/insights-worker' },
            ],
          },
        ],
        '/reference/': [
          {
            text: 'Reference',
            items: [
              { text: 'HTTP API', link: '/reference/api' },
              { text: 'Changelog', link: '/reference/changelog' },
              { text: 'License', link: '/reference/license' },
            ],
          },
        ],
      },
      socialLinks: [{ icon: 'github', link: REPO }],
      search: { provider: 'local' },
      editLink: { pattern: `${REPO}/edit/${BRANCH}/docs/:path`, text: 'Edit this page on GitHub' },
      outline: { level: [2, 3] },
      footer: {
        message: 'Code © Beili (Echo) Yin, all rights reserved. Data licensed by its publishers. Not financial advice.',
        copyright: 'NeighborIQ contributors',
      },
    },
  }),
)
