import axios from 'axios'
import router from '@/router'

const baseApiUrl = import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL + '/api' : '/api'

const instance = axios.create({
    baseURL: baseApiUrl,
    timeout: 15000,
    headers: {},
})

// Concurrent refresh dedup
let isRefreshing = false
let pendingRequests: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = []

instance.interceptors.request.use(config => {
    const token = localStorage.getItem('1-token')
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
        // Only handle 401
        if (!error.response || error.response.status !== 401) {
            return Promise.reject(error)
        }

        // If already refreshing, queue this request
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
            // Retry queued requests
            pendingRequests.forEach(p => p.resolve(newToken))
            pendingRequests = []
            error.config.headers['Authorization'] = 'Bearer ' + newToken
            return instance(error.config)
        } catch (refreshErr: any) {
            pendingRequests.forEach(p => p.reject(refreshErr))
            pendingRequests = []

            // Only logout if refresh returned 401 (token truly expired/invalid)
            if (refreshErr?.response?.status === 401) {
                localStorage.removeItem('1-token')
                localStorage.removeItem('1-refresh')
                localStorage.setItem('1-isLoggedIn', 'false')
                router.push('/login')
            }
            // Network errors, timeouts, 5xx from refresh → stay logged in
            return Promise.reject(refreshErr)
        } finally {
            isRefreshing = false
        }
    }
)

const refreshToken = async (): Promise<string> => {
    const refresh = localStorage.getItem('1-refresh')
    if (!refresh) {
        return Promise.reject(new Error('No refresh token available'))
    }

    const response = await axios.post(
        import.meta.env.VITE_API_URL + '/api/token/refresh/',
        { refresh: refresh }
    )

    if (response.data && response.data.access) {
        localStorage.setItem('1-token', response.data.access)
        return response.data.access
    }
    return Promise.reject(new Error('Invalid refresh response'))
}

export default instance
