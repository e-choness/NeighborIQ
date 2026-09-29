#!/usr/bin/env node
/**
 * Palette validator for src/theme/palette.ts (docs/development/frontend.md#colour).
 *
 *   node scripts/check-palette.mjs        # exits 1 when a check fails
 *
 * Checks, per theme:
 *   - step visibility: adjacent sequential steps differ by ΔE(OKLab) ≥ 0.035 and are ordered by lightness;
 *   - CVD separation: the same, after simulating protan/deutan/tritan vision (Machado et al. 2009, severity 1);
 *   - ground contrast: the strongest end of the ramp reaches ≥ 3:1 (WCAG non-text) against the basemap earth;
 *   - markers: subject vs comp ΔE ≥ 0.08 in every vision type, each ≥ 3:1 against the earth;
 *   - glass: text, text-2 and muted (src/styles/app.css) reach 4.5:1 on the glass panel composited over
 *     the basemap ground and its brightest area (light: white roads; dark: the lightest road grey).
 */
import { readFileSync } from 'node:fs'

const src = readFileSync(new URL('../src/theme/palette.ts', import.meta.url), 'utf8')
const block = (name) => src.slice(src.indexOf(`export const ${name}`)).split('\n}\n')[0]
const hexes = (s) => s.match(/#[0-9a-f]{6}/gi) ?? []
const modes = ['dark', 'light']
const line = (text, mode) => text.split('\n').find((l) => l.trim().startsWith(`${mode}:`))

const SEQUENTIAL = Object.fromEntries(modes.map((m) => [m, hexes(line(block('SEQUENTIAL'), m))]))
const MARKERS = Object.fromEntries(modes.map((m) => [m, hexes(line(block('MARKERS'), m))]))
const BASEMAP = block('BASEMAP')
const EARTH = {
  dark: BASEMAP.split('light:')[0].match(/earth: '(#[0-9a-f]{6})'/i)[1],
  light: BASEMAP.split('light:')[1].match(/earth: '(#[0-9a-f]{6})'/i)[1],
}

const toRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
const lin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
const luminance = (h) => {
  const [r, g, b] = toRgb(h).map(lin)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
const contrast = (a, b) => {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}
function oklab([r, g, b]) {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
  return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s]
}
const CVD = {
  normal: null,
  protan: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  deutan: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.01182, 0.04294, 0.968881]],
  tritan: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.3039]],
}
const simulate = (h, type) => {
  const rgb = toRgb(h).map(lin)
  const M = CVD[type]
  const out = M ? M.map((row) => Math.min(1, Math.max(0, row[0] * rgb[0] + row[1] * rgb[1] + row[2] * rgb[2]))) : rgb
  return oklab(out)
}
const dE = (a, b, type) => Math.hypot(...simulate(a, type).map((v, i) => v - simulate(b, type)[i]))

let failed = 0
const check = (ok, msg) => {
  console.log(`${ok ? '  ok ' : 'FAIL '} ${msg}`)
  if (!ok) failed++
}

for (const mode of modes) {
  const ramp = SEQUENTIAL[mode]
  const earth = EARTH[mode]
  console.log(`\n${mode}: ramp ${ramp.join(' ')} on earth ${earth}`)
  for (const type of Object.keys(CVD)) {
    const steps = ramp.slice(1).map((c, i) => dE(ramp[i], c, type))
    check(Math.min(...steps) >= 0.035, `${type.padEnd(6)} min adjacent step ΔE ${Math.min(...steps).toFixed(3)} (≥ 0.035)`)
  }
  const L = ramp.map((c) => simulate(c, 'normal')[0])
  const monotonic = L.slice(1).every((l, i) => (mode === 'dark' ? l > L[i] : l < L[i]))
  check(monotonic, `lightness ordered ${mode === 'dark' ? 'dark → light' : 'light → dark'} (${L.map((l) => l.toFixed(2)).join(' ')})`)
  const strongest = ramp.at(-1)
  check(contrast(strongest, earth) >= 3, `strongest step ${strongest} vs earth ${contrast(strongest, earth).toFixed(2)}:1 (≥ 3)`)

  const [subject, comp] = MARKERS[mode]
  for (const type of Object.keys(CVD)) {
    check(dE(subject, comp, type) >= 0.08, `${type.padEnd(6)} subject ${subject} vs comp ${comp} ΔE ${dE(subject, comp, type).toFixed(3)} (≥ 0.08)`)
  }
  for (const c of [subject, comp]) check(contrast(c, earth) >= 3, `marker ${c} vs earth ${contrast(c, earth).toFixed(2)}:1 (≥ 3)`)
}


// Text on glass: --panel composited over the basemap (blur averages, so solid grounds are the bounds)
const css = readFileSync(new URL('../src/styles/app.css', import.meta.url), 'utf8')
const tokens = (mode) => {
  const body = mode === 'light' ? css.slice(css.indexOf(':root {'), css.indexOf(':root[data-theme="dark"]')) : css.slice(css.indexOf(':root[data-theme="dark"]'))
  const get = (name) => body.match(new RegExp(`--${name}: ([^;]+);`))[1].trim()
  return { panel: get('panel'), text: get('text'), 'text-2': get('text-2'), muted: get('muted') }
}
const BRIGHTEST = { dark: '#3a4a44', light: '#ffffff' }
const over = (rgba, ground) => {
  const [r, g, b, a] = rgba.match(/[\d.]+/g).map(Number)
  const base = toRgb(ground).map((c) => c * 255)
  return '#' + [r, g, b].map((c, i) => Math.round(c * a + base[i] * (1 - a)).toString(16).padStart(2, '0')).join('')
}
for (const mode of modes) {
  const t = tokens(mode)
  console.log(`\n${mode}: glass ${t.panel}`)
  for (const ground of [EARTH[mode], BRIGHTEST[mode]]) {
    const bg = over(t.panel, ground)
    for (const key of ['text', 'text-2', 'muted']) {
      check(contrast(t[key], bg) >= 4.5, `${key.padEnd(6)} ${t[key]} on glass over ${ground} (${bg}) ${contrast(t[key], bg).toFixed(2)}:1 (≥ 4.5)`)
    }
  }
}
console.log(failed ? `\n${failed} check(s) failed` : '\nAll palette checks passed')
process.exit(failed ? 1 : 0)
