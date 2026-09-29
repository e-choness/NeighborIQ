#!/usr/bin/env node
/**
 * Records the README walkthrough from a running stack (docker compose up, demo data):
 * Map → Explore → Listing (value, cash flow) → Analyze → light theme.
 *
 *   docker run --rm -v "$PWD:/repo" -w /repo/frontend -e BASE_URL=http://host.docker.internal \
 *     [-e REDUCED_MOTION=1] neighboriq-test-frontend-e2e node scripts/walkthrough.mjs
 *
 * Writes a WebM to $OUT_DIR (default test-results/walkthrough); convert it with ffmpeg
 * (see docs/development/testing.md#walkthrough).
 */
import { mkdirSync, renameSync } from 'node:fs'
import { chromium } from '@playwright/test'

const BASE = process.env.BASE_URL ?? 'http://localhost'
const OUT = process.env.OUT_DIR ?? 'test-results/walkthrough'
const SIZE = { width: 1280, height: 800 }
mkdirSync(OUT, { recursive: true })

// A visible cursor with click ripples, and a caption bar in the app's glass style
const overlay = () => {
  const css = document.createElement('style')
  css.textContent = `
    #wt-cursor{position:fixed;z-index:99999;left:0;top:0;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;
      background:rgba(234,239,236,.9);border:2px solid #2b4638;box-shadow:0 2px 10px rgba(0,0,0,.45);pointer-events:none;transition:transform .12s}
    #wt-cursor.down{transform:scale(.7)}
    .wt-ripple{position:fixed;z-index:99998;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;border:2px solid #a9cdb2;
      pointer-events:none;animation:wt-r .6s ease-out forwards}
    @keyframes wt-r{from{transform:scale(.3);opacity:1}to{transform:scale(1.4);opacity:0}}
    #wt-caption{position:fixed;z-index:99997;transform:translateX(-50%);display:flex;align-items:center;gap:12px;
      padding:12px 18px 12px 12px;border-radius:18px;background:rgba(16,20,19,.8);border:1px solid rgba(255,255,255,.12);
      box-shadow:inset 0 1px 0 rgba(255,255,255,.07),0 24px 60px rgba(0,0,0,.45);backdrop-filter:blur(22px) saturate(1.5);
      color:#eaefec;font:500 15px 'Geist Variable',system-ui,sans-serif;white-space:nowrap;pointer-events:none;transition:opacity .3s}
    #wt-caption b{display:grid;place-items:center;min-width:30px;height:30px;padding:0 8px;border-radius:10px;background:#2b4638;
      color:#e4f1e7;font:500 12px 'Geist Mono Variable',monospace}
    #wt-caption span{color:#aab6af;font-weight:400}`
  const add = () => {
    document.head.appendChild(css)
    const c = document.createElement('div')
    c.id = 'wt-cursor'
    document.body.appendChild(c)
    addEventListener('mousemove', (e) => (c.style.left = `${e.clientX}px`, c.style.top = `${e.clientY}px`), true)
    addEventListener('mousedown', (e) => {
      c.classList.add('down')
      const r = document.createElement('div')
      r.className = 'wt-ripple'
      r.style.left = `${e.clientX}px`
      r.style.top = `${e.clientY}px`
      document.body.appendChild(r)
      setTimeout(() => r.remove(), 700)
    }, true)
    addEventListener('mouseup', () => c.classList.remove('down'), true)
  }
  if (document.body) add()
  else addEventListener('DOMContentLoaded', add)
  // Captions sit in open map area: beside the left sheet, or beside the right one (listing)
  window.__caption = (step, title, sub, at = { x: 884, bottom: 28 }) => {
    let el = document.getElementById('wt-caption')
    if (!el) {
      el = document.createElement('div')
      el.id = 'wt-caption'
      document.body.appendChild(el)
    }
    el.innerHTML = `<b>${step}</b>${title}<span>${sub}</span>`
    el.style.left = `${at.x}px`
    el.style.bottom = `${at.bottom}px`
  }
}

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] })
// REDUCED_MOTION=1: the app's reduced-motion mode (no orbit, instant camera) — far smaller GIFs
const reducedMotion = process.env.REDUCED_MOTION ? 'reduce' : 'no-preference'
const context = await browser.newContext({ viewport: SIZE, colorScheme: 'dark', reducedMotion, recordVideo: { dir: OUT, size: SIZE } })
await context.addInitScript(() => localStorage.setItem('niq-theme', 'dark'))
await context.addInitScript(overlay)
const page = await context.newPage()
const wait = (ms) => page.waitForTimeout(ms)
const caption = (step, title, sub, at) => page.evaluate(([a, b, c, d]) => window.__caption(a, b, c, d), [step, title, sub, at])
async function glide(target, steps = 25) {
  const box = await target.boundingBox()
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps })
  return box
}
async function click(target) {
  await glide(target)
  await wait(150)
  await page.mouse.down()
  await wait(90)
  await page.mouse.up()
}

// 1 · Map
await page.goto(`${BASE}/?city=Toronto`)
await page.waitForSelector('.maplibregl-canvas')
await page.mouse.move(640, 420)
await caption('01', 'Map · a city at a glance', ' — each column is ~0.7 km², height and colour show the metric', { x: 776, bottom: 178 })
await wait(3500)
await click(page.getByRole('button', { name: '$/sq ft' }))
await wait(2200)
await click(page.getByRole('button', { name: 'Price cuts' }))
await wait(2200)
await click(page.getByRole('button', { name: 'Yield', exact: true }))
await wait(1200)

// 2 · Explore
await caption('02', 'Explore · filter the listings', ' — the list and the dots on the map stay in sync')
await click(page.getByRole('link', { name: /Browse Toronto listings/ }))
await page.waitForSelector('ol button')
await wait(2200)
await click(page.getByRole('button', { name: 'Condo', exact: true }))
await wait(1500)
const rows = page.locator('ol button')
for (let i = 0; i < 4; i++) {
  await glide(rows.nth(i), 12)
  await wait(700)
}

// 3 · Listing
await caption('03', 'Listing · is the price fair?', ' — asking price against comparables, drawn on the map', { x: 440, bottom: 28 })
await click(rows.first())
await page.waitForSelector('[aria-label="Listing sections"]')
await wait(3000)
const sheet = page.locator('section').filter({ has: page.locator('[aria-label="Listing sections"]') }).locator('> div').last()
await sheet.evaluate((el) => el.scrollTo({ top: 420, behavior: 'smooth' }))
await wait(1500)
const comps = page.locator('ul li a[href^="/listings/"]')
for (let i = 0; i < Math.min(3, await comps.count()); i++) {
  await glide(comps.nth(i), 12)
  await wait(900)
}

// 4 · Cash flow
await caption('04', 'Cash flow · will it pay for itself?', ' — Canadian mortgage rules, every assumption adjustable', { x: 440, bottom: 28 })
await click(page.getByRole('tab', { name: 'Cash flow' }))
await page.getByTestId('monthly-cash-flow').waitFor()
await sheet.evaluate((el) => {
  // Bring the monthly cash flow just under the sticky tabs
  const cf = el.querySelector('[data-testid="monthly-cash-flow"]')
  el.scrollBy({ top: cf.getBoundingClientRect().top - el.getBoundingClientRect().top - 110, behavior: 'smooth' })
})
await wait(1800)
const rent = page.getByRole('slider', { name: 'Monthly rent' })
await rent.scrollIntoViewIfNeeded()
await wait(600)
const r = await glide(rent)
await page.mouse.down()
await page.mouse.move(r.x + r.width / 2 + 90, r.y + r.height / 2, { steps: 30 })
await page.mouse.up()
await wait(1800)

// 5 · Analyze
await caption('05', 'Analyze · any property', ' — from an address or a neighbourhood, with nearby comparables')
await click(page.getByRole('link', { name: 'Analyze' }))
await page.waitForSelector('#a-hood')
await wait(1200)
await glide(page.locator('#a-hood'))
await page.locator('#a-hood').selectOption({ index: 5 })
await wait(3500)
await page.getByRole('region', { name: 'Result' }).evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }))
await wait(2200)

// 6 · Light theme
await caption('06', 'Light or dark', ' — the whole app follows your theme', { x: 776, bottom: 178 })
await click(page.getByRole('link', { name: 'Map', exact: true }))
await wait(2500)
await click(page.getByRole('button', { name: 'Use light theme' }))
await wait(3500)

const video = page.video()
await context.close()
await browser.close()
renameSync(await video.path(), `${OUT}/walkthrough.webm`)
console.log(`${OUT}/walkthrough.webm`)
