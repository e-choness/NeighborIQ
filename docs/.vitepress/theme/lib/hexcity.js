// Isometric hexagon "city": the motif of the app's home map (H3 cells extruded by
// a metric). Shared by the docs hero (HexCity.vue) and the README banner
// generator (scripts/banner.mjs), so both draw the same scene.
//
// Pure geometry, no DOM: returns prisms sorted back-to-front with SVG path
// strings for the top face and the three visible side faces.

/** Validated sequential ramps from frontend/src/theme/palette.ts (low → high). */
export const RAMPS = {
  dark: ['#115e59', '#0f766e', '#0d9488', '#14b8a6', '#2dd4bf', '#5eead4'],
  light: ['#14b8a6', '#0d9488', '#0f766e', '#115e59'],
}

export const SURFACE = {
  dark: { bg: '#0b0f14', ink: '#e6edf3', muted: '#8b98a9', faint: '#1a2430', subject: '#3987e5' },
  light: { bg: '#f7f8fa', ink: '#0f1720', muted: '#526070', faint: '#dde3ea', subject: '#2a78d6' },
}

const SQUASH = 0.52 // vertical squash of the ground plane (isometric look)
const SQRT3 = Math.sqrt(3)

function mulberry32(seed) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

/** Mix colour a toward b by t (0..1). */
export function mix(a, b, t) {
  const [r1, g1, b1] = hexToRgb(a)
  const [r2, g2, b2] = hexToRgb(b)
  const c = (x, y) => Math.round(x + (y - x) * t).toString(16).padStart(2, '0')
  return `#${c(r1, r2)}${c(g1, g2)}${c(b1, b2)}`
}

const pt = (x, y) => `${x.toFixed(1)},${y.toFixed(1)}`

/**
 * @param {object} o
 * @param {number} o.width   scene width in px
 * @param {number} o.height  scene height in px
 * @param {number} o.cx      centre of the city (x)
 * @param {number} o.cy      centre of the city (y, ground plane)
 * @param {number} o.rx      horizontal radius of the city footprint
 * @param {number} o.r       hexagon radius
 * @param {number} o.maxH    tallest prism in px
 * @param {number} [o.seed]
 */
export function hexCity({ cx, cy, rx, r, maxH, seed = 7 }) {
  const rand = mulberry32(seed)
  const ry = rx * SQUASH
  // A few "neighbourhoods" with high values, like yield hot spots on the real map
  const peaks = [
    { x: cx - rx * 0.35, y: cy - ry * 0.1, s: rx * 0.32, a: 1.0 },
    { x: cx + rx * 0.3, y: cy + ry * 0.2, s: rx * 0.25, a: 0.8 },
    { x: cx + rx * 0.05, y: cy - ry * 0.45, s: rx * 0.2, a: 0.55 },
  ]
  const field = (x, y) =>
    peaks.reduce((sum, p) => {
      const dx = (x - p.x) / p.s
      const dy = (y - p.y) / (p.s * SQUASH)
      return sum + p.a * Math.exp(-(dx * dx + dy * dy))
    }, 0)

  const dx = r * 1.5
  const dy = r * SQRT3 * SQUASH
  const cols = Math.ceil(rx / dx) + 1
  const rows = Math.ceil(ry / dy) + 1
  const drawR = r * 0.88 // gap between cells

  const prisms = []
  for (let q = -cols; q <= cols; q++) {
    for (let row = -rows; row <= rows; row++) {
      const x = cx + q * dx
      const y = cy + (row + (Math.abs(q) % 2) / 2) * dy
      const ex = (x - cx) / rx
      const ey = (y - cy) / ry
      const d = ex * ex + ey * ey
      if (d > 1) continue
      // Sparse edges: fewer cells toward the rim
      if (d > 0.55 && rand() < (d - 0.55) * 1.6) continue
      const t = Math.min(1, Math.max(0, field(x, y) * 0.9 + rand() * 0.18 - 0.04))
      prisms.push({ x, y, t, d })
    }
  }
  prisms.sort((a, b) => a.y - b.y || a.x - b.x)

  return prisms.map((p, i) => {
    const h = 4 + p.t * maxH
    const v = []
    for (let k = 0; k < 6; k++) {
      const a = (Math.PI / 3) * k
      v.push([p.x + drawR * Math.cos(a), p.y + drawR * Math.sin(a) * SQUASH])
    }
    const up = (pv) => [pv[0], pv[1] - h]
    const face = (i1, i2) =>
      `M${pt(...up(v[i1]))}L${pt(...up(v[i2]))}L${pt(...v[i2])}L${pt(...v[i1])}Z`
    return {
      id: i,
      x: p.x,
      y: p.y,
      h,
      t: p.t,
      rim: p.d, // 0 at the centre, 1 at the edge — used to fade and to stagger animation
      top: `M${v.map((pv) => pt(...up(pv))).join('L')}Z`,
      right: face(0, 1),
      front: face(1, 2),
      left: face(2, 3),
    }
  })
}

/** Colours for one prism: top from the ramp by value; sides shaded toward the background. */
export function prismColors(t, mode) {
  const ramp = RAMPS[mode]
  const top = ramp[Math.min(ramp.length - 1, Math.round(t * (ramp.length - 1)))]
  const bg = SURFACE[mode].bg
  const shade = mode === 'dark' ? '#000000' : '#0b1a1a'
  return {
    top,
    right: mix(top, shade, mode === 'dark' ? 0.28 : 0.18),
    front: mix(top, shade, mode === 'dark' ? 0.42 : 0.3),
    left: mix(top, shade, mode === 'dark' ? 0.55 : 0.4),
    edge: mix(top, bg, 0.5),
  }
}
