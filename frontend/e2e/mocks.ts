/**
 * API mocks for the browser tests: route-intercepts /api/v1/* with fixtures exported from the
 * demo data (Toronto). Cash flow is recomputed from the posted rent so slider changes show up,
 * and saves are kept in memory so Save → Portfolio works.
 */
import type { Page, Route } from '@playwright/test'
import communities from './fixtures/communities-toronto.json' with { type: 'json' }
import cashflow from './fixtures/cashflow.json' with { type: 'json' }
import house from './fixtures/house.json' with { type: 'json' }
import houses from './fixtures/houses-toronto.json' with { type: 'json' }
import insights from './fixtures/insights.json' with { type: 'json' }
import markets from './fixtures/markets.json' with { type: 'json' }
import neighbourhood from './fixtures/neighbourhood.json' with { type: 'json' }
import points from './fixtures/points-toronto.json' with { type: 'json' }
import priceHistory from './fixtures/price-history.json' with { type: 'json' }

export const LISTING_ID = house.id
const USER = { id: 1, email: 'demo@neighboriq.ca', name: 'Demo User', role: 'user' }
const EMPTY_STYLE = { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#0c100f' } }] }

export async function mockApi(page: Page, opts: { signedIn?: boolean } = {}) {
  const saved: { id: number; house_id: number; saved_at: string; notes: null; assumptions: unknown; house: typeof house }[] = []
  const json = (route: Route, body: unknown, status = 200) =>
    route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })

  // Offline runs: a background-only stand-in for the hosted basemap style
  if (!process.env.CI_NETWORK) {
    await page.route('https://tiles.openfreemap.org/**', (route) => json(route, EMPTY_STYLE))
  }

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname.replace('/api/v1', '')
    const method = route.request().method()

    if (path === '/auth/me') return opts.signedIn ? json(route, USER) : json(route, { detail: 'Not authenticated' }, 401)
    if (path === '/auth/refresh') return json(route, { detail: 'No session' }, 401)
    if (path === '/markets') return json(route, markets)
    if (path.startsWith('/markets/') && path.endsWith('/points')) return json(route, points)
    if (path === '/communities') return json(route, communities)
    if (path === '/houses') {
      const size = Number(url.searchParams.get('page_size') ?? 20)
      return json(route, { ...houses, page_size: size, items: houses.items.slice(0, size) })
    }
    const one = path.match(/^\/houses\/(\d+)(\/.*)?$/)
    if (one) {
      const sub = one[2] ?? ''
      if (sub === '') return json(route, { ...house, id: Number(one[1]) })
      if (sub === '/insights') return json(route, { ...insights, house_id: Number(one[1]) })
      if (sub === '/price-history') return json(route, priceHistory)
      if (sub === '/neighbourhood') return json(route, neighbourhood)
    }
    if (path === '/cashflow' && method === 'POST') {
      const body = route.request().postDataJSON() as { monthly_rent: number }
      const delta = body.monthly_rent - cashflow.gross_monthly_income
      return json(route, {
        ...cashflow,
        gross_monthly_income: body.monthly_rent,
        effective_monthly_income: cashflow.effective_monthly_income + delta,
        monthly_cash_flow: cashflow.monthly_cash_flow + delta,
        annual_cash_flow: (cashflow.monthly_cash_flow + delta) * 12,
      })
    }
    if (path === '/portfolio/saved' && method === 'GET') return json(route, saved)
    if (path === '/portfolio/save' && method === 'POST') {
      const body = route.request().postDataJSON() as { house_id: number; assumptions: unknown }
      saved.push({ id: saved.length + 1, house_id: body.house_id, saved_at: new Date().toISOString(), notes: null, assumptions: body.assumptions, house })
      return json(route, saved[saved.length - 1], 201)
    }
    if (path.startsWith('/portfolio/saved/') && method === 'DELETE') {
      saved.splice(saved.findIndex((d) => d.house_id === Number(path.split('/').pop())), 1)
      return route.fulfill({ status: 204 })
    }
    if (path === '/data-sources' || path === '/indicators') return json(route, { items: [] })
    return json(route, { detail: `not mocked: ${method} ${path}` }, 404)
  })
}
