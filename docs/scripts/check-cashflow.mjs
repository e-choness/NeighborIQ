// Fails when the docs' JavaScript calculator disagrees with the Python one
// (via the shared fixtures). Runs before every docs build.
import { readFileSync } from 'node:fs'
import { compute } from '../.vitepress/theme/lib/cashflow.js'

const cases = JSON.parse(readFileSync(new URL('../.vitepress/theme/lib/cashflow.fixtures.json', import.meta.url)))

const close = (a, b) => {
  if (a && typeof a === 'object' && !Array.isArray(a))
    return Object.keys(a).length === Object.keys(b).length && Object.keys(a).every((k) => close(a[k], b[k]))
  if (typeof a === 'number' && typeof b === 'number') return Math.abs(a - b) <= 0.011
  return JSON.stringify(a) === JSON.stringify(b)
}

let failed = 0
for (const { input, output } of cases) {
  const actual = compute(input)
  for (const key of Object.keys(output)) {
    if (!close(output[key], actual[key])) {
      failed++
      console.error(`${input.city} ${input.price}: ${key} expected ${JSON.stringify(output[key])}, got ${JSON.stringify(actual[key])}`)
    }
  }
}
if (failed) {
  console.error(`\n${failed} mismatch(es) between cashflow.js and shared/analytics/cashflow.py`)
  process.exit(1)
}
console.log(`cashflow.js matches the Python calculator on ${cases.length} cases`)
