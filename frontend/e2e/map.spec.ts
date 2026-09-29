import { expect, test } from '@playwright/test'
import { LISTING_ID, mockApi } from './mocks'

type MapHandle = { getLayer(id: string): unknown; getStyle(): { layers: unknown[] } | undefined; getZoom(): number; loaded(): boolean }
declare global {
  interface Window { __hexmap?: MapHandle }
}

test.beforeEach(async ({ page }) => mockApi(page))

test('home map renders full-bleed with the hex layer', async ({ page }, info) => {
  await page.goto('/')
  const canvas = page.locator('.maplibregl-canvas')
  await expect(canvas).toBeVisible()
  const box = await canvas.boundingBox()
  const viewport = page.viewportSize()!
  // The map fills the window behind the glass panels
  expect(box!.width).toBeGreaterThanOrEqual(viewport.width - 1)
  expect(box!.height).toBeGreaterThanOrEqual(viewport.height - 1)
  if (info.project.name === 'desktop') {
    expect(box!.width).toBeGreaterThan(600)
    expect(box!.height).toBeGreaterThan(400)
  }
  await expect.poll(() => page.evaluate(() => Boolean(window.__hexmap?.getLayer('hex')))).toBe(true)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('across Toronto')
  await page.screenshot({ path: info.outputPath('home.png') })
})

test('hosted basemap loads streets under the data', async ({ page }) => {
  test.skip(!process.env.CI_NETWORK, 'needs network access to tiles.openfreemap.org')
  await page.goto('/')
  await expect.poll(() => page.evaluate(() => window.__hexmap?.getStyle()?.layers.length ?? 0)).toBeGreaterThan(1)
  await expect(page.getByText('Basemap unreachable')).toHaveCount(0)
})

test('returning from a listing to the map refits the city', async ({ page }, info) => {
  // 1280px: the width where stacked listing + home paddings no longer fit
  if (info.project.name === 'desktop') await page.setViewportSize({ width: 1280, height: 800 })
  const zoom = () => page.evaluate(() => window.__hexmap?.getZoom() ?? 0)
  await page.goto(`/listings/${LISTING_ID}`)
  await expect.poll(zoom).toBeGreaterThan(13.5)
  // In-app navigation keeps the same map: it must leave street level for the city view
  await page.getByRole('link', { name: 'Map', exact: true }).click()
  await expect(page).toHaveURL(/\/$/)
  await expect.poll(zoom).toBeLessThan(13)
})
