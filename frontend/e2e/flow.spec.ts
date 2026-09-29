import { expect, test } from '@playwright/test'
import { LISTING_ID, mockApi } from './mocks'

test('best yield → listing → cash flow → save → portfolio', async ({ page }, info) => {
  await mockApi(page, { signedIn: true })
  await page.goto('/')

  // Desktop shows the best yields as floating cards; phones list them in the sheet
  const best = page.getByRole('button', { name: /\$\d+K.*yield/ }).first()
  await best.scrollIntoViewIfNeeded()
  await best.click()
  await expect(page).toHaveURL(new RegExp(`/listings/${LISTING_ID}`))
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await page.screenshot({ path: info.outputPath('listing.png') })

  // Tabs are shareable through ?tab=
  await page.getByRole('tab', { name: 'Cash flow' }).click()
  await expect(page).toHaveURL(/tab=cash/)
  const cash = page.getByTestId('monthly-cash-flow')
  await expect(cash).toBeVisible()
  const before = await cash.innerText()

  // Raise the rent with the slider (keyboard drag): the monthly cash flow follows
  const rent = page.getByRole('slider', { name: 'Monthly rent' })
  await rent.focus()
  for (let i = 0; i < 8; i++) await rent.press('ArrowRight')
  await expect(cash).not.toHaveText(before)

  await page.getByRole('button', { name: 'Save deal' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Saved to portfolio' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Saved' })).toBeVisible()

  await page.goto('/portfolio')
  await expect(page.getByTestId('portfolio-row')).toHaveCount(1)
  await page.screenshot({ path: info.outputPath('portfolio.png') })
})

test('explore list rows open the listing and back restores the filters', async ({ page }, info) => {
  await mockApi(page)
  await page.goto('/explore?city=Toronto&cut=1')
  await expect(page.getByRole('heading', { name: 'Toronto listings' })).toBeVisible()
  // Phones: pull the sheet up (half → full) so the list clears the tab bar
  if (info.project.name === 'phone') await page.getByRole('button', { name: 'Resize panel' }).click()
  await page.locator('ol button').first().click()
  await expect(page).toHaveURL(/\/listings\/\d+/)
  await page.getByRole('link', { name: 'Close' }).click()
  await expect(page).toHaveURL(/\/explore\?.*cut=1/)
})
