import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/search',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/pages/LoginPage.vue'),
      meta: { requiresAuth: false, hideForAuth: true },
    },
    {
      path: '/search',
      name: 'Search',
      component: () => import('@/pages/SearchPage.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/portfolio',
      name: 'Portfolio',
      component: () => import('@/pages/PortfolioPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      name: 'Admin',
      component: () => import('@/pages/AdminPage.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/search',
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // Check auth state if not yet loaded
  if (authStore.user === null && !authStore.loading) {
    await authStore.checkAuth()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next({ name: 'Search' })
  }

  if (to.meta.hideForAuth && authStore.isAuthenticated) {
    return next({ name: 'Search' })
  }

  next()
})

export default router
