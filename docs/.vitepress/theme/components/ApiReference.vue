<script setup lang="ts">
/** Searchable HTTP API reference, generated at build time from services/api/openapi.json. */
import { computed, ref } from 'vue'
import { data } from '../../../reference/api.data.js'

type Field = { name: string; type: string; required: boolean; default: string; description: string }
type Endpoint = {
  id: string
  method: string
  path: string
  tag: string
  summary: string
  description: string
  auth: 'public' | 'user' | 'admin'
  params: (Field & { in: string })[]
  body: { name: string | null; fields: Field[] } | null
  response: { name: string | null; fields: Field[] } | null
}

const endpoints = data.endpoints as Endpoint[]
const tags = [...new Set(endpoints.map((e) => e.tag))]
const query = ref('')
const tag = ref('')

const shown = computed(() => {
  const q = query.value.trim().toLowerCase()
  return endpoints.filter(
    (e) =>
      (!tag.value || e.tag === tag.value) &&
      (!q || `${e.method} ${e.path} ${e.summary} ${e.description}`.toLowerCase().includes(q)),
  )
})

const AUTH_LABEL = { public: 'Public', user: 'Signed in', admin: 'Admin' }

function curl(e: Endpoint) {
  const required = e.params.filter((p) => p.in === 'query' && p.required)
  const qs = required.length ? '?' + required.map((p) => `${p.name}=…`).join('&') : ''
  const lines = [`curl -X ${e.method.toUpperCase()} "http://localhost:8000${e.path}${qs}"`]
  if (e.auth !== 'public') lines.push(`  -H "Authorization: Bearer $TOKEN"`)
  if (e.body) {
    const example = Object.fromEntries(
      e.body.fields.filter((f) => f.required).map((f) => [f.name, f.type.startsWith('number') || f.type.startsWith('integer') ? 0 : '…']),
    )
    lines.push(`  -H "Content-Type: application/json"`, `  -d '${JSON.stringify(example)}'`)
  }
  return lines.join(' \\\n')
}
</script>

<template>
  <div class="api">
    <div class="bar">
      <input v-model="query" type="search" placeholder="Filter endpoints — e.g. cashflow, areas, POST" aria-label="Filter endpoints" />
      <div class="tags" role="group" aria-label="Filter by area">
        <button type="button" :aria-pressed="tag === ''" @click="tag = ''">All</button>
        <button v-for="t in tags" :key="t" type="button" :aria-pressed="tag === t" @click="tag = tag === t ? '' : t">{{ t }}</button>
      </div>
    </div>
    <p class="count">{{ shown.length }} of {{ endpoints.length }} endpoints · {{ data.title }} {{ data.version }}</p>

    <details v-for="e in shown" :id="e.id" :key="e.id" class="ep">
      <summary>
        <span class="method" :class="e.method">{{ e.method.toUpperCase() }}</span>
        <code class="path">{{ e.path }}</code>
        <span class="summary">{{ e.summary }}</span>
        <span class="auth" :class="e.auth">{{ AUTH_LABEL[e.auth] }}</span>
      </summary>
      <div class="body">
        <p v-if="e.description">{{ e.description }}</p>

        <template v-if="e.params.length">
          <h4>Parameters</h4>
          <table>
            <thead><tr><th>Name</th><th>In</th><th>Type</th><th>Default</th><th>Description</th></tr></thead>
            <tbody>
              <tr v-for="p in e.params" :key="p.in + p.name">
                <td><code>{{ p.name }}</code><span v-if="p.required" class="req" title="required">required</span></td>
                <td>{{ p.in }}</td>
                <td><code class="type">{{ p.type }}</code></td>
                <td><code v-if="p.default">{{ p.default }}</code></td>
                <td>{{ p.description }}</td>
              </tr>
            </tbody>
          </table>
        </template>

        <template v-for="(part, label) in { 'Request body': e.body, Response: e.response }" :key="label">
          <template v-if="part && part.fields.length">
            <h4>{{ label }} <code v-if="part.name">{{ part.name }}</code></h4>
            <table>
              <thead><tr><th>Field</th><th>Type</th><th>Default</th><th>Description</th></tr></thead>
              <tbody>
                <tr v-for="f in part.fields" :key="f.name">
                  <td><code>{{ f.name }}</code><span v-if="f.required" class="req">required</span></td>
                  <td><code class="type">{{ f.type }}</code></td>
                  <td><code v-if="f.default">{{ f.default }}</code></td>
                  <td>{{ f.description }}</td>
                </tr>
              </tbody>
            </table>
          </template>
          <p v-else-if="part && part.name" class="muted">{{ label }}: <code>{{ part.name }}</code></p>
        </template>

        <h4>Example</h4>
        <div class="language-sh"><pre><code>{{ curl(e) }}</code></pre></div>
      </div>
    </details>
  </div>
</template>

<style scoped>
.bar {
  display: grid;
  gap: 10px;
  margin: 16px 0 8px;
}
.bar input {
  width: 100%;
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  padding: 8px 12px;
  background: var(--vp-c-bg-soft);
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tags button {
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 13px;
}
.tags button[aria-pressed='true'] {
  border-color: var(--vp-c-brand-1);
  color: var(--vp-c-brand-1);
}
.bar input:focus-visible,
.tags button:focus-visible,
summary:focus-visible {
  outline: 2px solid var(--vp-c-brand-1);
  outline-offset: 2px;
}
.count {
  font-size: 13px;
  color: var(--vp-c-text-2);
}
.ep {
  border: 1px solid var(--vp-c-divider);
  border-radius: 10px;
  margin: 8px 0;
  background: var(--vp-c-bg);
}
.ep[open] {
  background: var(--vp-c-bg-soft);
}
summary {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  list-style: none;
  flex-wrap: wrap;
  border-radius: 10px;
}
summary::-webkit-details-marker {
  display: none;
}
.method {
  font-family: var(--vp-font-family-mono);
  font-size: 12px;
  font-weight: 700;
  min-width: 58px;
  text-align: center;
  border-radius: 6px;
  padding: 2px 6px;
  border: 1px solid var(--vp-c-divider);
  color: var(--vp-c-text-1);
}
.method.get {
  background: var(--vp-c-brand-soft);
  border-color: transparent;
  color: var(--vp-c-brand-1);
}
.path {
  font-size: 14px;
  background: none !important;
  padding: 0 !important;
}
.summary {
  color: var(--vp-c-text-2);
  font-size: 14px;
}
.auth {
  margin-left: auto;
  font-size: 12px;
  border-radius: 999px;
  padding: 1px 8px;
  border: 1px solid var(--vp-c-divider);
  color: var(--vp-c-text-2);
}
.auth.admin {
  color: var(--vp-c-text-1);
  border-color: var(--vp-c-text-3);
}
.body {
  padding: 0 14px 12px;
}
.body h4 {
  margin: 16px 0 6px;
  font-size: 14px;
}
.body table {
  display: table;
  width: 100%;
  font-size: 13px;
  margin: 0;
}
.req {
  margin-left: 6px;
  font-size: 11px;
  color: var(--vp-c-text-2);
}
.type {
  white-space: normal;
  word-break: break-word;
}
.muted {
  color: var(--vp-c-text-2);
  font-size: 13px;
}
.language-sh {
  border-radius: 8px;
}
.language-sh pre {
  margin: 0;
  padding: 12px 14px;
  overflow-x: auto;
  font-size: 13px;
}
</style>
