import http from './request'
import { ref } from 'vue'

// 使用ref直接管理登录状态
export const isLoggedIn = ref(localStorage.getItem("1-isLoggedIn") === "true")

export default {
  login(data: any) {
    return http.post('/admin-login/', data).then(res => {
      isLoggedIn.value = true
      localStorage.setItem("1-isLoggedIn", "true")
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
    return http.get('/admin/details/');
  },

  // 请求重置密码邮件
  requestPasswordReset(email: string) {
    return http.post('/password-reset/', { email })
  },
  // 确认重置密码
  confirmPasswordReset(data: { email: string, reset_code: string, new_password: string }) {
    return http.post('/password-reset/confirm/', data)
  },
  // 获取分页用户信息
  getUsers(params: {
    page: number;
    page_size: number;
    query?: string;
    role?: string;
    permission?: string;
    startTime?: string;
    endTime?: string;
  }) {
    return http.get('/get_users/', { params });
  },
  // 删除用户
  deleteUser(userId: number) {
    return http.delete(`/delete_user/${userId}/`)
  },
  // 更新用户权限
  updateUserPermission(userId: number, permissionName: string) {
    return http.post(`/user_permission/${userId}/`, {
      permission: permissionName
    })
  },
  // 创建管理员
  createAdmin(data: {
    username: string;
    email: string;
    password: string;
    role?: string;
  }) {
    return http.post('/create-admin/', data)
  },
  // 获取其他用户信息
  getOtherUserInfo(userId: number) {
    return http.get(`/admin/details/${userId}`);
  },

  // 获取管理员详情
  getAdminDetail(userId: number) {
    return http.get(`/admin/details/${userId}`);
  },

  // 获取专家邀请码
  getInviteCode(data: any) {
    return http.get(`/organization/${data.organization_id}/invitation_codes/`)
  }
}
