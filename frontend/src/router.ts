import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    /** Where the page's sheet docks over the persistent map; `plain` has no map or shell. */
    layout?: 'map-left' | 'map-right' | 'map-center' | 'plain'
    auth?: boolean
    admin?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/pages/HomePage.vue'), meta: { layout: 'map-left' } },
    { path: '/explore', name: 'explore', component: () => import('@/pages/ExplorePage.vue'), meta: { layout: 'map-left' } },
    { path: '/analyze', name: 'analyze', component: () => import('@/pages/AnalyzePage.vue'), meta: { layout: 'map-left' } },
    {
      path: '/listings/:id',
      name: 'listing',
      component: () => import('@/pages/ListingPage.vue'),
      props: (r) => ({ id: Number(r.params.id) }),
      meta: { layout: 'map-right' },
    },
    { path: '/portfolio', name: 'portfolio', component: () => import('@/pages/PortfolioPage.vue'), meta: { layout: 'map-center', auth: true } },
    { path: '/data', name: 'data', component: () => import('@/pages/DataPage.vue'), meta: { layout: 'map-center' } },
    { path: '/admin', redirect: { path: '/data', query: { tab: 'admin' } } },
    { path: '/login', name: 'login', component: () => import('@/pages/LoginPage.vue'), meta: { layout: 'plain' } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuth()
  await auth.check()
  if (to.meta.auth && !auth.isAuthenticated) return { name: 'login', query: { next: to.fullPath } }
  if (to.meta.admin && !auth.isAdmin) return { name: 'home' }
})

export default router
