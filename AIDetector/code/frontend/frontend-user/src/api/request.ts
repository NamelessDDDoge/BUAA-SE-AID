import axios from 'axios'
import router from '@/router'

const apiBaseUrl = import.meta.env.VITE_API_URL || ''

const instance = axios.create({
  baseURL: `${apiBaseUrl}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

let isRefreshing = false
let pendingRequests: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = []

instance.interceptors.request.use(config => {
  let token = localStorage.getItem('2-token')
  if (token) {
    config.headers['Authorization'] = 'Bearer ' + token
  }
  return config
}, error => {
  return Promise.reject(error)
})

instance.interceptors.response.use(
  response => response,
  async error => {
    if (!error.response || error.response.status !== 401) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingRequests.push({ resolve, reject })
      }).then(token => {
        error.config.headers['Authorization'] = 'Bearer ' + token
        return instance(error.config)
      })
    }

    isRefreshing = true

    try {
      const newToken = await refreshToken()
      pendingRequests.forEach(p => p.resolve(newToken))
      pendingRequests = []
      error.config.headers['Authorization'] = 'Bearer ' + newToken
      return instance(error.config)
    } catch (refreshErr: any) {
      pendingRequests.forEach(p => p.reject(refreshErr))
      pendingRequests = []

      if (refreshErr?.response?.status === 401) {
        localStorage.removeItem('2-token')
        localStorage.removeItem('2-refresh')
        router.push('/login')
      }
      return Promise.reject(refreshErr)
    } finally {
      isRefreshing = false
    }
  }
)

const refreshToken = async (): Promise<string> => {
  const refresh = localStorage.getItem('2-refresh')
  if (!refresh) {
    return Promise.reject(new Error('No refresh token available'))
  }

  const response = await axios.post(
    `${apiBaseUrl}/api/token/refresh/`,
    { refresh: refresh }
  )

  if (response.data && response.data.access) {
    localStorage.setItem('2-token', response.data.access)
    return response.data.access
  }
  return Promise.reject(new Error('Invalid refresh response'))
}

export default instance
