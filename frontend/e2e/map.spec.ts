import { expect, test } from '@playwright/test'
import { mockApi } from './mocks'

type MapHandle = { getLayer(id: string): unknown; getStyle(): { layers: unknown[] } | undefined; loaded(): boolean }
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
