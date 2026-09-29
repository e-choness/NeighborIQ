#!/usr/bin/env node
/**
 * Screenshots for the README and docs (docs/public/media) from a running stack (docker compose up, demo data).
 *
 *   docker run --rm -v "$PWD:/repo" -w /repo/frontend -e BASE_URL=http://host.docker.internal \
 *     neighboriq-test-frontend-e2e node scripts/docs-screenshots.mjs
 *
 * Writes docs/public/media/{home,explore,listing,analyze}.png (desktop, dark) plus -light and -phone variants;
 * the README and docs use home-light, home-phone and listing-phone (delete the others).
 */
import { chromium, devices } from '@playwright/test'

const BASE = process.env.BASE_URL ?? 'http://localhost'
const OUT = process.env.OUT_DIR ?? '../docs/public/media'
const settle = (page, ms = 3500) => page.waitForTimeout(ms)

async function listingId(page) {
  const r = await page.request.get(`${BASE}/api/v1/houses?city=Toronto&sort=gross_yield&order=desc&page_size=1`)
  return (await r.json()).items[0].id
}

async function shoot(browser, { suffix, theme, context }) {
  const ctx = await browser.newContext({ ...context, colorScheme: theme, reducedMotion: 'reduce' })
  await ctx.addInitScript((t) => localStorage.setItem('niq-theme', t), theme)
  const page = await ctx.newPage()
  const id = await listingId(page)
  const shots = [
    ['home', '/?city=Toronto'],
    ['explore', '/explore?city=Toronto'],
    ['listing', `/listings/${id}`],
    ['analyze', '/analyze?city=Toronto'],
  ]
  for (const [name, path] of shots) {
    await page.goto(`${BASE}${path}`)
    await page.waitForSelector('.maplibregl-canvas')
    if (name === 'analyze') {
      const hood = page.locator('#a-hood')
      await hood.selectOption({ index: 1 })
    }
    await settle(page)
    await page.screenshot({ path: `${OUT}/${name}${suffix}.png` })
    console.log(`${OUT}/${name}${suffix}.png`)
  }
  await ctx.close()
}

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
await shoot(browser, { suffix: '', theme: 'dark', context: { viewport: { width: 1440, height: 900 } } })
await shoot(browser, { suffix: '-light', theme: 'light', context: { viewport: { width: 1440, height: 900 } } })
await shoot(browser, { suffix: '-phone', theme: 'dark', context: { ...devices['iPhone 14'] } })
await browser.close()
