// Generates the README banners (animated SVG, dark + light) and the social card, in the app's
// visual language: sage hexagon map, glass tiles, Italiana wordmark, Geist and Geist Mono, Lucide icons.
//
//   npm run banner            (from docs/, after npm install)
//
// Output (all in docs/public/media): banner-dark.svg, banner-light.svg, og-card.svg, logo.svg;
// also frontend/public/favicon.svg (the same mark).
// The fonts are embedded (base64 WOFF2) because GitHub renders README SVGs as isolated images.
// Render the card to PNG (social previews need a raster image):
//   render og-card.svg at 1280×640 after ~3.5 s (once the animation has settled) to docs/public/media/og.png
import { readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { hexCity, prismColors, SURFACE } from '../.vitepress/theme/lib/hexcity.js'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const require = createRequire(import.meta.url)
const font = (pkg, file) =>
  readFileSync(resolve(dirname(require.resolve(`${pkg}/package.json`)), 'files', file)).toString('base64')

const FONTS = `
  @font-face{font-family:'NIQ Display';src:url(data:font/woff2;base64,${font('@fontsource/italiana', 'italiana-latin-400-normal.woff2')}) format('woff2')}
  @font-face{font-family:'NIQ Sans';font-weight:100 900;src:url(data:font/woff2;base64,${font('@fontsource-variable/geist', 'geist-latin-wght-normal.woff2')}) format('woff2')}
  @font-face{font-family:'NIQ Mono';font-weight:100 900;src:url(data:font/woff2;base64,${font('@fontsource-variable/geist-mono', 'geist-mono-latin-wght-normal.woff2')}) format('woff2')}
  .display{font-family:'NIQ Display','Didot',serif}
  .sans{font-family:'NIQ Sans',ui-sans-serif,system-ui,sans-serif}
  .mono{font-family:'NIQ Mono',ui-monospace,monospace}`

// Lucide icons (ISC licence), 24×24 stroke paths
const ICONS = {
  scale: '<path d="M12 3v18"/><path d="m19 8 3 8a5 5 0 0 1-6 0zV7"/><path d="M3 7h1a17 17 0 0 0 8-2 17 17 0 0 0 8 2h1"/><path d="m5 8 3 8a5 5 0 0 1-6 0zV7"/><path d="M7 21h10"/>',
  calculator: '<rect width="16" height="20" x="4" y="2" rx="2"/><line x1="8" x2="16" y1="6" y2="6"/><line x1="16" x2="16" y1="14" y2="18"/><path d="M16 10h.01"/><path d="M12 10h.01"/><path d="M8 10h.01"/><path d="M12 14h.01"/><path d="M8 14h.01"/><path d="M12 18h.01"/><path d="M8 18h.01"/>',
  mapPin: '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
}
const MARK = '<path d="M12 2 21 7.2v9.6L12 22l-9-5.2V7.2L12 2Zm0 3.5L6 9v6l6 3.5 6-3.5V9l-6-3.5Z"/><path d="M12 9.2 14.4 10.6v2.8L12 14.8l-2.4-1.4v-2.8L12 9.2Z"/>'

const TILES = [
  ['scale', 'Fair value', 'vs nearest comparables'],
  ['calculator', 'Cash flow', 'Canadian mortgage rules'],
  ['mapPin', 'Neighbourhood', 'from public open data'],
]

const GLASS = {
  dark: { fill: 'rgb(16,20,19)', fillOpacity: 0.75, edge: 'rgba(255,255,255,0.10)', hi: 'rgba(255,255,255,0.07)', chip: 'rgba(255,255,255,0.05)', line: 'rgba(255,255,255,0.08)', shadow: '#000', shadowOpacity: 0.45 },
  light: { fill: 'rgb(250,252,251)', fillOpacity: 0.72, edge: 'rgba(255,255,255,0.9)', hi: 'rgba(255,255,255,0.85)', chip: 'rgba(14,19,17,0.045)', line: 'rgba(14,19,17,0.09)', shadow: '#14221b', shadowOpacity: 0.16 },
}

/** A glass panel: translucent fill, 1px light edge, inner top highlight, soft drop shadow. */
function glass(mode, x, y, w, h, r, extra = '') {
  const g = GLASS[mode]
  return (
    `<rect x="${x}" y="${y + 10}" width="${w}" height="${h}" rx="${r}" fill="${g.shadow}" opacity="${g.shadowOpacity}" filter="url(#soft)"/>` +
    `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" fill="${g.fill}" fill-opacity="${g.fillOpacity}" stroke="${g.edge}"${extra}/>` +
    `<path d="M${x + r} ${y + 1}H${x + w - r}" stroke="${g.hi}" stroke-width="1"/>`
  )
}

function iconChip(mode, x, y, size, icon) {
  const s = SURFACE[mode]
  const g = GLASS[mode]
  const k = (size * 0.47) / 24
  const off = (size - 24 * k) / 2
  return (
    `<rect x="${x}" y="${y}" width="${size}" height="${size}" rx="${size * 0.32}" fill="${g.chip}" stroke="${g.line}"/>` +
    `<g transform="translate(${x + off} ${y + off}) scale(${k.toFixed(3)})" fill="none" stroke="${s.accent}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${ICONS[icon]}</g>`
  )
}

function scene({ mode, width, height, city, text, card, animate }) {
  const s = SURFACE[mode]
  const g = GLASS[mode]
  const prisms = hexCity(city)
  const minX = Math.min(...prisms.map((p) => p.x))
  const maxX = Math.max(...prisms.map((p) => p.x))
  // The subject: a tall cell near the main hot spot, with comp-search rings around it
  const subject = prisms.filter((p) => p.rim < 0.35).reduce((best, p) => (p.t > best.t ? p : best), { t: -1 })
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
  .in{animation:rise .9s cubic-bezier(.2,.8,.2,1) both}.l1{animation-delay:.1s}.l2{animation-delay:.25s}.l3{animation-delay:.4s}.l4{animation-delay:.55s}.l5{animation-delay:.7s}.card{animation-delay:1.9s}
  @keyframes rise{from{opacity:0;transform:translateY(8px)}}
  @media (prefers-reduced-motion: reduce){*{animation:none!important}.ring{opacity:.5}}`
    : `.ring{opacity:.55}`

  const t = text
  const tiles = TILES.map(([icon, label, sub], i) => {
    const x = t.stack ? t.x : t.x + i * (t.tileW + t.tileGap)
    const y = t.stack ? t.tileY + i * (t.tileH + t.tileGap) : t.tileY
    const ic = t.tileH - 24
    return (
      `<g class="in l${i + 3}">` +
      glass(mode, x, y, t.tileW, t.tileH, 18) +
      iconChip(mode, x + 12, y + 12, ic, icon) +
      `<text class="sans" x="${x + 24 + ic}" y="${y + t.tileH / 2 - 3}" font-size="${t.tileLabel}" font-weight="500" fill="${s.ink}">${label}</text>` +
      `<text class="sans" x="${x + 24 + ic}" y="${y + t.tileH / 2 + t.tileSub + 1}" font-size="${t.tileSub}" fill="${s.muted}">${sub}</text>` +
      `</g>`
    )
  }).join('')

  // A floating "best yield" card, as on the app's home screen
  const c = card
  const best =
    `<g class="in card">` +
    glass(mode, c.x, c.y, c.w, c.h, 18) +
    `<rect x="${c.x + 14}" y="${c.y + 14}" width="34" height="34" rx="11" fill="${g.chip}" stroke="${g.line}"/>` +
    `<g transform="translate(${c.x + 20} ${c.y + 20}) scale(0.92)" fill="${s.accent}">${MARK}</g>` +
    `<text class="sans" x="${c.x + 60}" y="${c.y + 27}" font-size="10.5" letter-spacing="1.2" fill="${s.muted}">BEST YIELD · 01</text>` +
    `<text class="mono" x="${c.x + 60}" y="${c.y + 46}" font-size="16" font-weight="500" fill="${s.ink}">$443K <tspan font-size="12.5" fill="${s.accent}">4.5% yield</tspan></text>` +
    `</g>`

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title desc">
<title id="title">NeighborIQ</title>
<desc id="desc">Rental-property analysis for small investors in Canadian cities: fair value from comparable listings, cash flow under Canadian mortgage rules, and neighbourhood open data. Illustration: the app's hexagon map, where height and colour show a metric.</desc>
<style>${FONTS}${css}</style>
<defs>
  <radialGradient id="glow" cx="0.72" cy="0.6" r="0.55">
    <stop offset="0" stop-color="${s.accent}" stop-opacity="${mode === 'dark' ? 0.14 : 0.28}"/>
    <stop offset="1" stop-color="${s.bg}" stop-opacity="0"/>
  </radialGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M32 0H0V32" fill="none" stroke="${s.faint}" stroke-width="1" opacity="${mode === 'dark' ? 0.6 : 0.8}"/>
  </pattern>
  <linearGradient id="gridfade" x1="0" x2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.45" stop-color="#fff" stop-opacity="0.5"/><stop offset="1" stop-color="#fff" stop-opacity="1"/>
  </linearGradient>
  <mask id="gm"><rect width="100%" height="100%" fill="url(#gridfade)"/></mask>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="160%"><feGaussianBlur stdDeviation="14"/></filter>
</defs>
<rect width="100%" height="100%" rx="${t.radius}" fill="${s.bg}"/>
<rect width="100%" height="100%" rx="${t.radius}" fill="url(#grid)" mask="url(#gm)"/>
<rect width="100%" height="100%" rx="${t.radius}" fill="url(#glow)"/>
<g>${cells}</g>
<g>${rings}<circle class="dot" cx="${subject.x.toFixed(1)}" cy="${sy.toFixed(1)}" r="5" fill="${s.subject}" stroke="${s.bg}" stroke-width="2"/></g>
${best}
<text class="mono in l1" x="${t.x}" y="${t.y - t.title * 0.95}" font-size="${t.eyebrow}" letter-spacing="${t.eyebrow * 0.14}" fill="${s.muted}">CANADIAN CITIES · RENTAL PROPERTY</text>
<text class="display in l1" x="${t.x - 2}" y="${t.y}" font-size="${t.title}" letter-spacing="${t.title * 0.03}" fill="${s.ink}">Neighbor<tspan fill="${s.accent}">IQ</tspan></text>
<text class="sans in l2" x="${t.x}" y="${t.y + t.sub}" font-size="${t.lead}" fill="${s.muted}">Rental-property analysis for small investors in Canadian cities</text>
${tiles}
</svg>
`
}

/**
 * The mark: a small honeycomb of extruded hexagon columns, the map's own motif, on a deep green-black tile.
 * Column tops come from the app's sage ramp (taller = higher on the ramp, as on the map).
 * Drawn with the same isometric squash as the hero illustration.
 */
function logo() {
  const SQUASH = 0.52
  const R = 6.1 // drawn radius; cells sit on a honeycomb with a small gap
  const dx = R * 1.5 * 1.1
  const dy = R * Math.sqrt(3) * SQUASH * 1.1
  const cx = 32
  const cy = 43.5
  const s = SURFACE.dark
  const pt = (x, y) => `${x.toFixed(2)},${y.toFixed(2)}`
  // [column, row offset, height, ramp position]: a hot spot toward the upper left, like the map's yield peaks
  const cells = [
    [0, -1, 8, 0.3],
    [-1, -0.5, 25, 1],
    [1, -0.5, 7, 0.2],
    [0, 0, 17, 0.75],
    [-1, 0.5, 13, 0.55],
    [1, 0.5, 10, 0.4],
    [0, 1, 11, 0.45],
  ]
  // back to front: by ground y, then x
  const columns = cells
    .map(([q, r, h, t]) => [cx + q * dx, cy + r * dy, h, t])
    .sort((a, b) => a[1] - b[1] || a[0] - b[0])
  const prisms = columns
    .map(([x, y, h, t]) => {
      const c = prismColors(t, 'dark')
      const v = Array.from({ length: 6 }, (_, k) => [x + R * Math.cos((Math.PI / 3) * k), y + R * Math.sin((Math.PI / 3) * k) * SQUASH])
      const up = ([px, py]) => [px, py - h]
      const face = (a, b) => `M${pt(...up(v[a]))}L${pt(...up(v[b]))}L${pt(...v[b])}L${pt(...v[a])}Z`
      const top = `M${v.map((p) => pt(...up(p))).join('L')}Z`
      return (
        `<path d="${face(2, 3)}" fill="${c.left}"/><path d="${face(1, 2)}" fill="${c.front}"/><path d="${face(0, 1)}" fill="${c.right}"/>` +
        `<path d="${top}" fill="${c.top}" stroke="${c.edge}" stroke-width=".5" stroke-linejoin="round"/>`
      )
    })
    .join('')
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="NeighborIQ">
<defs>
  <linearGradient id="tile" x1="0" y1="0" x2="0.9" y2="1"><stop offset="0" stop-color="#1a2a22"/><stop offset="1" stop-color="${s.bg}"/></linearGradient>
  <radialGradient id="glow" cx="0.5" cy="0.62" r="0.55"><stop offset="0" stop-color="${s.accent}" stop-opacity=".22"/><stop offset="1" stop-color="${s.accent}" stop-opacity="0"/></radialGradient>
</defs>
<rect width="64" height="64" rx="15" fill="url(#tile)"/>
<rect width="64" height="64" rx="15" fill="url(#glow)"/>
<rect x=".5" y=".5" width="63" height="63" rx="14.5" fill="none" stroke="#fff" stroke-opacity=".12"/>
${prisms}
</svg>
`
}

// Everything visual lives in docs/public/media (the docs site serves it as /media/*, the README links to it).
// The app's favicon is generated from the same mark so the two can't drift apart.
const media = resolve(root, 'docs/public/media')
const banner = {
  width: 1280,
  height: 360,
  city: { cx: 1000, cy: 200, rx: 250, r: 13.5, maxH: 88, seed: 11 },
  card: { x: 1030, y: 30, w: 210, h: 62 },
  text: { x: 56, y: 132, eyebrow: 12, sub: 38, title: 72, lead: 18, radius: 16, tileY: 214, tileW: 206, tileH: 64, tileGap: 12, tileLabel: 15, tileSub: 12 },
}
for (const mode of ['dark', 'light']) {
  writeFileSync(resolve(media, `banner-${mode}.svg`), scene({ mode, ...banner, animate: true }))
}

// Social card: 1280×640, same animation as the banner (og.png, the still crawlers use, is rendered from it)
writeFileSync(
  resolve(media, 'og-card.svg'),
  scene({
    mode: 'dark',
    width: 1280,
    height: 640,
    city: { cx: 900, cy: 470, rx: 390, r: 19, maxH: 130, seed: 11 },
    card: { x: 960, y: 70, w: 240, h: 62 },
    text: { x: 72, y: 190, eyebrow: 15, sub: 52, title: 104, lead: 24, radius: 0, tileY: 290, tileW: 330, tileH: 76, tileGap: 16, tileLabel: 18, tileSub: 14, stack: true },
    animate: true,
  }),
)

const mark = logo()
writeFileSync(resolve(media, 'logo.svg'), mark)
writeFileSync(resolve(root, 'frontend/public/favicon.svg'), mark)
console.log('wrote docs/public/media/{banner-dark,banner-light,og-card,logo}.svg and frontend/public/favicon.svg')
