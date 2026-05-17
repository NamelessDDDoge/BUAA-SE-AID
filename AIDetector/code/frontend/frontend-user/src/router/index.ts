/**
 * router/index.ts
 *
 * Automatic routes for `./src/pages/*.vue`
 */

// Composables
import { createRouter, createWebHistory } from 'vue-router/auto'
import { setupLayouts } from 'virtual:generated-layouts'
import { routes } from 'vue-router/auto-routes'
import { isLoggedIn } from '@/api/user'
import pinia from '@/stores'
import { useUserStore } from '@/stores/user'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: setupLayouts(routes),
})

// Workaround for https://github.com/vitejs/vite/issues/11804
router.onError((err, to) => {
  if (err?.message?.includes?.('Failed to fetch dynamically imported module')) {
    if (!localStorage.getItem('vuetify:dynamic-reload')) {
      console.log('Reloading page to fix dynamic import error')
      localStorage.setItem('vuetify:dynamic-reload', 'true')
      location.assign(to.fullPath)
    } else {
      console.error('Dynamic import error, reloading page did not fix it', err)
    }
  } else {
    console.error(err)
  }
})

router.isReady().then(() => {
  localStorage.removeItem('vuetify:dynamic-reload')
})

const normalizePath = (path: string) => path.replace(/\/+$/, '') || '/'

const startsWithRoute = (path: string, prefix: string) => {
  return path === prefix || path.startsWith(`${prefix}/`)
}

const isPublisherOnlyRoute = (path: string) => {
  if (['/upload', '/history', '/annual'].includes(path)) return true
  if (startsWithRoute(path, '/step')) return true
  if (startsWithRoute(path, '/task') && !startsWithRoute(path, '/task/detail')) return true
  return false
}

const isReviewerOnlyRoute = (path: string) => {
  return path === '/review' || startsWithRoute(path, '/task/detail')
}

router.beforeEach(async (to, from, next) => {
  if (!isLoggedIn.value) {
    if (to.path === '/login') {
      next()
    } else {
      next('/login')
    }
  } else {
    const userStore = useUserStore(pinia)
    if (!userStore.isLoaded) {
      const loaded = await userStore.fetchUserInfo()
      if (!loaded) {
        next()
        return
      }
    }

    const path = normalizePath(to.path)
    const role = userStore.role

    if (to.path === '/login') {
      next('/')
    } else if (role === 'reviewer' && isPublisherOnlyRoute(path)) {
      next('/review')
    } else if (role === 'publisher' && isReviewerOnlyRoute(path)) {
      next('/history')
    } else {
      next()
    }
  }
})




export default router
