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
  id: number;
  organization_name: string;
  organization: number
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
    id: 0,
    organization: 0,
    organization_name: ''
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
        this.isLoaded = true;
        this.id = response.data.id;
        this.organization = response.data.organizatio
        this.organization_name = response.data.organization_name
        return true;
      } catch (error) {
        console.error('获取用户信息失败:', error);
        this.isLoaded = false;
        return false;
      }
    },

    async updateAvatar(file: File) {
      try {
        const formData = new FormData();
        formData.append('avatar', file);

        const response = await user.updateUserAvatar(formData);
        if (response.data.avatar) {
          this.avatar = `${API_BASE_URL}${response.data.avatar}`;
          this.fetchUserInfo();
        }
        return true;
      } catch (error) {
        console.error('更新头像失败:', error);
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
      this.id = 0;
      this.organization = 0;
      this.organization_name = ''
    }
  },

  getters: {
    displayName: (state) => state.username || '未登录',
    userRole: (state) => state.role || '未设置',
    hasUserInfo: (state) => state.isLoaded
  }
}); 
