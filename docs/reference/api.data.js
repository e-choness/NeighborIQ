// Build-time loader: turns services/api/openapi.json (checked in CI to match the
// code) into the data behind the API reference page. Regenerate the snapshot
// with `python scripts/export_openapi.py`; the page follows automatically.
import { readFileSync } from 'node:fs'

const SPEC = new URL('../../services/api/openapi.json', import.meta.url)

// Access levels, mirroring the dependencies in services/api/app/security.py
function authFor(method, path) {
  if (path.startsWith('/api/v1/admin')) return 'admin'
  if (path.startsWith('/api/v1/houses') && method !== 'get') return 'admin'
  if (path.startsWith('/api/v1/portfolio')) return 'user'
  if (path === '/api/v1/auth/me' || path === '/api/v1/auth/logout') return 'user'
  return 'public'
}

const TAG_ORDER = ['listings', 'insights', 'places', 'portfolio', 'auth', 'admin', 'health']

export default {
  watch: ['../../services/api/openapi.json'],
  load() {
    const spec = JSON.parse(readFileSync(SPEC, 'utf8'))
    const schemas = spec.components?.schemas ?? {}

    const refName = (ref) => ref.split('/').pop()
    const typeOf = (s) => {
      if (!s) return 'any'
      if (s.$ref) return refName(s.$ref)
      if (s.anyOf) {
        const parts = s.anyOf.filter((x) => x.type !== 'null').map(typeOf)
        const nullable = s.anyOf.some((x) => x.type === 'null')
        return parts.join(' | ') + (nullable ? ' | null' : '')
      }
      if (s.enum) return s.enum.map((v) => JSON.stringify(v)).join(' | ')
      if (s.const !== undefined) return JSON.stringify(s.const)
      if (s.type === 'array') return `${typeOf(s.items)}[]`
      if (s.type === 'object' && s.additionalProperties) return `{ [key]: ${typeOf(s.additionalProperties)} }`
      return s.format ? `${s.type} (${s.format})` : (s.type ?? 'object')
    }
    const constraints = (s) => {
      const out = []
      for (const [k, sym] of [
        ['minimum', '≥'],
        ['exclusiveMinimum', '>'],
        ['maximum', '≤'],
        ['exclusiveMaximum', '<'],
        ['minLength', 'min length'],
        ['maxLength', 'max length'],
      ])
        if (s?.[k] !== undefined) out.push(`${sym} ${s[k]}`)
      return out.join(', ')
    }
    const fieldsOf = (schemaRef) => {
      if (!schemaRef) return null
      const name = schemaRef.$ref ? refName(schemaRef.$ref) : null
      const s = name ? schemas[name] : schemaRef
      if (!s?.properties) return { name: name ?? typeOf(schemaRef), fields: [] }
      const required = new Set(s.required ?? [])
      return {
        name,
        fields: Object.entries(s.properties).map(([field, p]) => ({
          name: field,
          type: typeOf(p),
          required: required.has(field),
          default: p.default !== undefined ? JSON.stringify(p.default) : '',
          description: [p.description ?? '', constraints(p)].filter(Boolean).join(' · '),
        })),
      }
    }

    const endpoints = []
    for (const [path, ops] of Object.entries(spec.paths)) {
      for (const [method, op] of Object.entries(ops)) {
        const ok = op.responses?.['200'] ?? op.responses?.['201']
        const description = (op.description ?? '').split('\n\n')[0].replace(/\n/g, ' ').trim()
        endpoints.push({
          id: op.operationId,
          method,
          path,
          tag: op.tags?.[0] ?? 'health',
          summary: op.summary ?? '',
          description,
          auth: authFor(method, path),
          params: (op.parameters ?? []).map((p) => ({
            name: p.name,
            in: p.in,
            type: typeOf(p.schema),
            required: !!p.required,
            default: p.schema?.default !== undefined ? JSON.stringify(p.schema.default) : '',
            description: [p.description ?? '', constraints(p.schema)].filter(Boolean).join(' · '),
          })),
          body: fieldsOf(op.requestBody?.content?.['application/json']?.schema),
          response: fieldsOf(ok?.content?.['application/json']?.schema),
        })
      }
    }
    const rank = (t) => (TAG_ORDER.includes(t) ? TAG_ORDER.indexOf(t) : 99)
    endpoints.sort((a, b) => rank(a.tag) - rank(b.tag) || a.path.localeCompare(b.path))

    return { title: spec.info.title, version: spec.info.version, endpoints }
  },
}
