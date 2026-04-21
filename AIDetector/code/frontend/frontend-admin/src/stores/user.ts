// stores/user.ts
import { defineStore } from 'pinia';
import user from '@/api/user';

interface UserState {
  username: string;
  email: string;
  role: string;
  profile: string;
  avatar: string;
  isLoaded: boolean;
  admin_type: string;
  organization: number;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const useUserStore = defineStore('user', {
  state: (): UserState => ({
    username: '',
    email: '',
    role: '',
    profile: '',
    avatar: './192.png',
    isLoaded: false,
    admin_type: '',
    organization: 0
  }),

  actions: {
    async fetchUserInfo() {
      try {
        const response = await user.getUserInfo();
        this.username = response.data.username || '';
        this.email = response.data.email || '';
        this.role = response.data.role || '';
        this.profile = response.data.profile || '';
        this.avatar = response.data.avatar ? `${API_BASE_URL}${response.data.avatar}` : './192.png';
        this.admin_type = response.data.admin_type;
        this.isLoaded = true;
        this.organization = response.data.organization;
        return true;
      } catch (error) {
        console.error('获取用户信息失败:', error);
        this.isLoaded = false;
        return false;
      }
    },

    clearUserInfo() {
      this.username = '';
      this.email = '';
      this.role = '';
      this.profile = '';
      this.avatar = './192.png';
      this.isLoaded = false;
      this.admin_type = '';
      this.organization = 0;
    }
  },

  getters: {
    displayName: (state) => state.username || '未登录',
    userRole: (state) => state.role || '未设置',
    hasUserInfo: (state) => state.isLoaded
  }
}); 
