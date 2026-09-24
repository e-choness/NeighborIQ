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
const EXCLUDE = ['scripts/**', '**/node_modules/**']
const excluded = (abs: string) => {
  const rel = relative(SRC, abs).split(sep).join('/')
  return rel.startsWith('scripts/')
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
    rewrites: { 'adr/README.md': 'adr/index.md' },
    head: [
      ['link', { rel: 'icon', type: 'image/svg+xml', href: `${BASE}logo.svg` }],
      ['meta', { name: 'theme-color', content: '#0b0f14' }],
      ['meta', { property: 'og:type', content: 'website' }],
      ['meta', { property: 'og:title', content: 'NeighborIQ' }],
      [
        'meta',
        {
          property: 'og:description',
          content: 'Is the price fair, will it cash-flow, what is the neighbourhood like — for Canadian rental properties.',
        },
      ],
      ['meta', { property: 'og:image', content: `${SITE}og.png` }],
      ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ],
    vite: { build: { chunkSizeWarningLimit: 2000 } }, // mermaid is large and loaded on demand
    markdown: {
      config: githubLinks,
      theme: { light: 'github-light', dark: 'github-dark-dimmed' },
    },
    themeConfig: {
      logo: '/logo.svg',
      siteTitle: 'NeighborIQ',
      nav: [
        { text: 'Guide', link: '/guide/', activeMatch: '^/(guide|development|DEPLOYMENT|operations)' },
        { text: 'How it works', link: '/methodology', activeMatch: '^/(methodology|data-sources)' },
        { text: 'Architecture', link: '/architecture/overview', activeMatch: '^/(architecture|services|frontend|adr)' },
        { text: 'API', link: '/reference/api', activeMatch: '^/reference' },
        {
          text: 'More',
          items: [
            { text: 'License', link: '/guide/license' },
            { text: 'Changelog', link: `${REPO}/blob/${BRANCH}/CHANGELOG.md` },
            { text: 'Contributing', link: `${REPO}/blob/${BRANCH}/CONTRIBUTING.md` },
            { text: 'Security policy', link: `${REPO}/blob/${BRANCH}/SECURITY.md` },
            { text: 'Issues', link: `${REPO}/issues` },
          ],
        },
      ],
      sidebar: [
        {
          text: 'Guide',
          items: [
            { text: 'Introduction', link: '/guide/' },
            { text: 'Development setup', link: '/development/getting-started' },
            { text: 'Deployment', link: '/DEPLOYMENT' },
            { text: 'Operations', link: '/operations' },
            { text: 'Testing', link: '/development/testing' },
            { text: 'License', link: '/guide/license' },
          ],
        },
        {
          text: 'How it works',
          items: [
            { text: 'Methodology', link: '/methodology' },
            { text: 'Cash-flow calculator', link: '/guide/calculator' },
            { text: 'Data sources', link: '/data-sources' },
          ],
        },
        {
          text: 'Architecture',
          items: [
            { text: 'Overview', link: '/architecture/overview' },
            { text: 'Data model', link: '/architecture/data-models' },
            { text: 'Frontend', link: '/frontend/overview' },
            {
              text: 'Services',
              collapsed: false,
              items: [
                { text: 'api', link: '/services/api' },
                { text: 'ingestion-worker', link: '/services/ingestion-worker' },
                { text: 'insights-worker', link: '/services/insights-worker' },
              ],
            },
          ],
        },
        {
          text: 'Reference',
          items: [{ text: 'HTTP API', link: '/reference/api' }],
        },
        {
          text: 'Decisions',
          collapsed: true,
          items: [
            { text: 'Index', link: '/adr/' },
            { text: '0001 One API, two workers', link: '/adr/0001-one-api-two-workers' },
            { text: '0002 Search in PostgreSQL', link: '/adr/0002-search-in-postgres' },
            { text: '0003 Open data, no scraping', link: '/adr/0003-open-data-and-synthetic-listings' },
            { text: '0004 Keep Celery', link: '/adr/0004-keep-celery' },
            { text: '0005 Licence (FSL)', link: '/adr/0005-license-fsl' },
          ],
        },
      ],
      socialLinks: [{ icon: 'github', link: REPO }],
      search: { provider: 'local' },
      editLink: { pattern: `${REPO}/edit/${BRANCH}/docs/:path`, text: 'Edit this page on GitHub' },
      outline: { level: [2, 3] },
      footer: {
        message: 'Code under the Functional Source License (FSL-1.1-ALv2). Data licensed by its publishers. Not financial advice.',
        copyright: 'NeighborIQ contributors',
      },
    },
  }),
)
