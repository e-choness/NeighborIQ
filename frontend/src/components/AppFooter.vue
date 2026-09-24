<script setup lang="ts">
import { useQuery } from '@pinia/colada'
import { RouterLink } from 'vue-router'
import { api } from '@/lib/api'
import type { DataSource } from '@/lib/types'

const { data } = useQuery({
  key: ['data-sources'],
  query: () => api<{ items: DataSource[] }>('/data-sources'),
})
</script>

<template>
  <footer class="border-t border-border">
    <div class="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-6 text-xs text-muted sm:flex-row sm:items-start sm:justify-between sm:px-6">
      <p class="max-w-2xl leading-relaxed">
        Estimates from asking prices and public data — not appraisals or advice.
        <template v-if="data?.items.length">
          Data: {{ [...new Set(data.items.map((s) => s.attribution).filter(Boolean))].join(' · ') }}.
        </template>
      </p>
      <RouterLink to="/data" class="shrink-0 text-text-2 hover:text-text">Sources &amp; methodology</RouterLink>
    </div>
  </footer>
</template>
