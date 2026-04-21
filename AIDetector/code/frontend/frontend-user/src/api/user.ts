import { da } from 'vuetify/locale'
import http from './request'
import { ref } from 'vue'

// 使用ref直接管理登录状态
export const isLoggedIn = ref(localStorage.getItem("2-isLoggedIn") === "true")

export default {
  login(data: any) {
    return http.post('/login/', data).then(res => {
      isLoggedIn.value = true
      localStorage.setItem("2-isLoggedIn", "true")
      return res
    })
  },
  register(data: any) {
    return http.post('/register/', data)
  },
  logout(data: any) {
    return http.post('/logout/', data).then(res => {
      isLoggedIn.value = false
      return res
    })
  },
  getUserInfo() {
    return http.get('/user/details/');
  },
  updateUserInfo(data: any) {
    return http.put('/user/update/', data)
  },
  updateUserAvatar(data: any) {
    return http.put('/user/avatar/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

  },
  // 请求重置密码邮件
  requestPasswordReset(email: string) {
    return http.post('/password-reset/', { email })
  },
  // 确认重置密码
  confirmPasswordReset(data: { email: string, reset_code: string, new_password: string }) {
    return http.post('/password-reset/confirm/', data)
  },

  createOrganization(data: any) {
    return http.post('/organization/create/', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}
