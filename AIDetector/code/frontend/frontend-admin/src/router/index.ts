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

const LOGIN_PATH = '/login'
const DEFAULT_ADMIN_PATH = '/analytics'

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

router.beforeEach((to, from, next) => {
  if (to.path === '/') {
    next(LOGIN_PATH)
    return
  }

  if (!isLoggedIn.value) {
    if (to.path === LOGIN_PATH) {
      next()
    } else {
      next(LOGIN_PATH)
    }
  } else {
    if (to.path === LOGIN_PATH && from.path !== '/') {
      next(DEFAULT_ADMIN_PATH)
    } else {
      next()
    }
  }
})
export default router
