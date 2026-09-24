// Generates the README banners (animated SVG, dark + light) and the social card.
//
//   node docs/scripts/banner.mjs
//
// Output: images/banner-dark.svg, images/banner-light.svg, docs/public/og-card.svg
// Render the card to PNG (social previews need a raster image):
//   npx playwright screenshot --viewport-size=1280,640 file://$PWD/docs/public/og-card.svg docs/public/og.png
import { writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { hexCity, prismColors, SURFACE } from '../.vitepress/theme/lib/hexcity.js'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')

const FONT = `ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`

const LINES = [
  ['Fair value', 'against the nearest comparable listings'],
  ['Cash flow', 'under Canadian mortgage rules, every input editable'],
  ['Neighbourhood', 'census, transit, crime and new supply from open data'],
]

function scene({ mode, width, height, city, text, animate }) {
  const s = SURFACE[mode]
  const prisms = hexCity(city)
  const minX = Math.min(...prisms.map((p) => p.x))
  const maxX = Math.max(...prisms.map((p) => p.x))
  // The subject: a tall cell near the main hot spot, with comp-search rings around it
  const subject = prisms
    .filter((p) => p.rim < 0.35)
    .reduce((best, p) => (p.t > best.t ? p : best), { t: -1 })
  const sy = subject.y - subject.h

  const cells = prisms
    .map((p) => {
      const c = prismColors(p.t, mode)
      const delay = (0.15 + ((p.x - minX) / (maxX - minX)) * 0.9 + p.rim * 0.25).toFixed(2)
      const fade = p.rim > 0.6 ? ` opacity="${(1 - (p.rim - 0.6) * 1.4).toFixed(2)}"` : ''
      const style = animate ? ` style="--d:${delay}s;--h:${p.h.toFixed(1)}px"` : ''
      return (
        `<g class="p"${style}${fade}>` +
        `<g class="s"><path d="${p.left}" fill="${c.left}"/><path d="${p.front}" fill="${c.front}"/><path d="${p.right}" fill="${c.right}"/></g>` +
        `<path class="t" d="${p.top}" fill="${c.top}" stroke="${c.edge}" stroke-width="0.6"/></g>`
      )
    })
    .join('')

  const rings = [1, 2, 3]
    .map(
      (k) =>
        `<ellipse class="ring r${k}" cx="${subject.x.toFixed(1)}" cy="${sy.toFixed(1)}" rx="${city.r * 2.2 * k}" ry="${(city.r * 2.2 * k * 0.52).toFixed(1)}" fill="none" stroke="${s.subject}" stroke-width="1.2"/>`,
    )
    .join('')

  const css = animate
    ? `
  .p .s{transform-box:fill-box;transform-origin:50% 100%;animation:grow 1.5s cubic-bezier(.2,.8,.2,1) var(--d) both}
  .p .t{animation:lift 1.5s cubic-bezier(.2,.8,.2,1) var(--d) both}
  @keyframes grow{from{transform:scaleY(0)}}
  @keyframes lift{from{transform:translateY(var(--h))}}
  .ring{transform-box:fill-box;transform-origin:50% 50%;opacity:0;animation:ring 4.5s ease-out 1.8s infinite}
  .r2{animation-delay:2.3s}.r3{animation-delay:2.8s}
  @keyframes ring{0%{opacity:0;transform:scale(.35)}20%{opacity:.9}100%{opacity:0;transform:scale(1)}}
  .dot{animation:pop .5s ease-out 1.6s both}
  @keyframes pop{from{opacity:0}}
  .txt{animation:fade .9s ease-out both}.l1{animation-delay:.2s}.l2{animation-delay:.35s}.l3{animation-delay:.5s}.l4{animation-delay:.65s}
  @keyframes fade{from{opacity:0}}
  @media (prefers-reduced-motion: reduce){*{animation:none!important}.ring{opacity:.5}}`
    : `.ring{opacity:.55}`

  const t = text
  const lines = t.compact
    ? `<g class="txt l2" transform="translate(${t.x} ${t.y + t.sub + t.gap})">` +
      LINES.map(
        ([k], i) =>
          `<g transform="translate(${i * t.compact} 0)"><rect x="0" y="-12" width="4" height="16" rx="2" fill="${prismColors(0.5 + i * 0.25, mode).top}"/>` +
          `<text x="14" y="0" font-size="${t.body}" fill="${s.ink}" font-weight="600">${k}</text></g>`,
      ).join('') +
      `</g>`
    : LINES.map(
        ([k, v], i) =>
          `<g class="txt l${i + 2}" transform="translate(${t.x} ${t.y + t.gap * (i + 1) + t.sub})">` +
          `<rect x="0" y="-11" width="3" height="14" rx="1.5" fill="${prismColors(0.5 + i * 0.25, mode).top}"/>` +
          `<text x="14" y="0" font-size="${t.body}" fill="${s.ink}" font-weight="600">${k}` +
          `<tspan fill="${s.muted}" font-weight="400"> — ${v}</tspan></text></g>`,
      ).join('')

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title desc" font-family="${FONT}">
<title id="title">NeighborIQ</title>
<desc id="desc">Rental-property analysis for small investors in Canadian cities: fair value from comparable listings, cash flow under Canadian mortgage rules, and neighbourhood open data. Illustration: a hexagon map where height and colour show a metric.</desc>
<style>${css}</style>
<defs>
  <radialGradient id="glow" cx="0.7" cy="0.62" r="0.55">
    <stop offset="0" stop-color="${mode === 'dark' ? '#0d9488' : '#99f6e4'}" stop-opacity="${mode === 'dark' ? 0.16 : 0.35}"/>
    <stop offset="1" stop-color="${s.bg}" stop-opacity="0"/>
  </radialGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M32 0H0V32" fill="none" stroke="${s.faint}" stroke-width="1" opacity="${mode === 'dark' ? 0.55 : 0.8}"/>
  </pattern>
  <linearGradient id="gridfade" x1="0" x2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.45" stop-color="#fff" stop-opacity="0.5"/><stop offset="1" stop-color="#fff" stop-opacity="1"/>
  </linearGradient>
  <mask id="gm"><rect width="100%" height="100%" fill="url(#gridfade)"/></mask>
</defs>
<rect width="100%" height="100%" rx="${t.radius}" fill="${s.bg}"/>
<rect width="100%" height="100%" rx="${t.radius}" fill="url(#grid)" mask="url(#gm)"/>
<rect width="100%" height="100%" rx="${t.radius}" fill="url(#glow)"/>
<g>${cells}</g>
<g>${rings}<circle class="dot" cx="${subject.x.toFixed(1)}" cy="${sy.toFixed(1)}" r="5" fill="${s.subject}" stroke="${s.bg}" stroke-width="2"/></g>
<g class="txt l1" transform="translate(${t.x} ${t.y})">
  <text font-size="${t.title}" font-weight="650" letter-spacing="-1.5" fill="${s.ink}">Neighbor<tspan fill="${prismColors(1, mode).top}">IQ</tspan></text>
  <text y="${t.sub}" font-size="${t.lead}" fill="${s.muted}">Rental-property analysis for small investors in Canadian cities</text>
</g>
${lines}
</svg>
`
}

const banner = {
  width: 1280,
  height: 360,
  city: { cx: 990, cy: 196, rx: 255, r: 13.5, maxH: 88, seed: 11 },
  text: { x: 56, y: 118, sub: 40, gap: 34, title: 64, lead: 19, body: 16, radius: 16 },
}
for (const mode of ['dark', 'light']) {
  writeFileSync(resolve(root, `images/banner-${mode}.svg`), scene({ mode, ...banner, animate: true }))
}

// Social card: 1280×640, static (GitHub/OG crawlers take the first frame of nothing)
writeFileSync(
  resolve(root, 'docs/public/og-card.svg'),
  scene({
    mode: 'dark',
    width: 1280,
    height: 640,
    city: { cx: 900, cy: 468, rx: 400, r: 19, maxH: 130, seed: 11 },
    text: { x: 72, y: 138, sub: 50, gap: 50, title: 96, lead: 26, body: 22, radius: 0, compact: 190 },
    animate: false,
  }),
)
console.log('wrote images/banner-{dark,light}.svg and docs/public/og-card.svg')
