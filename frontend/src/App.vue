<template>
  <div class="font-sans antialiased">
    <NavBar />
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import NavBar from '@/components/NavBar.vue'

const authStore = useAuthStore()

// Check auth state on app mount (reads HttpOnly cookie via /me endpoint)
onMounted(() => {
  authStore.checkAuth()

  // Listen for auth expiry events from the axios interceptor
  window.addEventListener('auth:expired', () => {
    authStore.logout()
  })
})
</script>
