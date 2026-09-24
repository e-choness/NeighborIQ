import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/pages/HomePage.vue'), meta: { fullBleed: true } },
    { path: '/explore', name: 'explore', component: () => import('@/pages/ExplorePage.vue'), meta: { fullBleed: true } },
    { path: '/listings/:id', name: 'listing', component: () => import('@/pages/ListingPage.vue'), props: (r) => ({ id: Number(r.params.id) }) },
    { path: '/analyze', name: 'analyze', component: () => import('@/pages/AnalyzePage.vue') },
    { path: '/portfolio', name: 'portfolio', component: () => import('@/pages/PortfolioPage.vue'), meta: { auth: true } },
    { path: '/admin', name: 'admin', component: () => import('@/pages/AdminPage.vue'), meta: { auth: true, admin: true } },
    { path: '/data', name: 'data', component: () => import('@/pages/DataPage.vue') },
    { path: '/login', name: 'login', component: () => import('@/pages/LoginPage.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

router.beforeEach(async (to) => {
  const auth = useAuth()
  await auth.check()
  if (to.meta.auth && !auth.isAuthenticated) return { name: 'login', query: { next: to.fullPath } }
  if (to.meta.admin && !auth.isAdmin) return { name: 'home' }
})

export default router
