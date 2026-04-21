<template>
  <v-app :theme="theme">
    <Snackbar />
    <!-- 只在非移动端显示侧边导航栏 -->
    <v-navigation-drawer v-if="!isMobile" v-model="drawer" :rail="rail" :permanent="true" :temporary="false"
      location="left" class="navigation-drawer" @mouseenter="rail = false" @mouseleave="rail = true"
      :width="rail ? 56 : 200">
      <v-list>
        <v-list-item :prepend-avatar="isLoggedIn ? userStore.avatar : undefined" :subtitle="getSubTitle(userStore.admin_type)"
          :title="userStore.displayName">
        </v-list-item>
      </v-list>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-home" title="主页" value="home" @click="goToHome"></v-list-item>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-chart-bar" title="统计分析" value="analytics"
          @click="goToAnalytics"></v-list-item>
        <v-list-item v-if="isLoggedIn && userStore.admin_type === 'software_admin'" 
          prepend-icon="mdi-office-building" title="组织管理" value="organizations"
          @click="goToOrganizations"></v-list-item>
        <v-list-item v-if="isLoggedIn && userStore.admin_type === 'organization_admin'" 
          prepend-icon="mdi-account-circle" title="组织信息" value="organization_profile"
          @click="goToOrganizationProfile"></v-list-item>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-folder" title="图像管理" value="files"
          @click="goToFiles"></v-list-item>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-account-group" title="用户管理" value="users"
          @click="goToUsers"></v-list-item>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-clipboard-text-clock" title="日志记录" value="logs"
          @click="goToLogs"></v-list-item>
        <v-list-item v-if="isLoggedIn && userStore.admin_type === 'organization_admin'" 
          prepend-icon="mdi-gavel" title="人工审核" value="reviewRequests"
          @click="goToReviews"></v-list-item>
        <v-divider class="my-2"></v-divider>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-logout" title="退出登录" value="logout"
          @click="handleLogout"></v-list-item>
        <v-list-item v-else prepend-icon="mdi-login" title="登录" value="login" @click="goToLogin"></v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar class="app-bar">
      <v-app-bar-nav-icon @click="drawer = !drawer" v-if="!isMobile"></v-app-bar-nav-icon>
      <v-toolbar-title>学术图像检测系统</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn :icon="theme === 'light' ? 'mdi-weather-sunny' : 'mdi-weather-night'" @click="toggleTheme"></v-btn>
      <!-- <v-btn v-if="isAdmin" :color="hasUnreadNotifications ? 'red' : ''"
        :icon="hasUnreadNotifications ? 'mdi-bell-badge' : 'mdi-bell-outline'"
        @click="showNotifications = true"></v-btn> -->
      <v-btn icon="mdi-broadcast" v-if="isLoggedIn && userStore.admin_type === 'software_admin'" @click="showBroadcastDialog = true"></v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>

    <!-- 移动端底部导航栏 -->
    <v-bottom-navigation v-if="isMobile">
      <v-btn to="/" value="home">
        <v-icon>mdi-home</v-icon>
        <span>主页</span>
      </v-btn>
      <v-btn v-if="isLoggedIn" to="/analytics" value="analytics">
        <v-icon>mdi-chart-bar</v-icon>
        <span>统计分析</span>
      </v-btn>
      
      <v-btn v-if="isLoggedIn && userStore.admin_type === 'software_admin'" to="/organizations" value="organizations">
        <v-icon>mdi-office-building</v-icon>
        <span>组织管理</span>
      </v-btn>
      <v-btn v-if="isLoggedIn && userStore.admin_type === 'organization_admin'" to="/organization_profile" value="organization_profile">
        <v-icon>mdi-account-circle</v-icon>
        <span>组织信息</span>
      </v-btn>
      <v-btn v-if="isLoggedIn" to="/files" value="files">
        <v-icon>mdi-folder</v-icon>
        <span>图像管理</span>
      </v-btn>
      <v-btn v-if="isLoggedIn" to="/users" value="users">
        <v-icon>mdi-account-group</v-icon>
        <span>用户管理</span>
      </v-btn>
      <v-btn v-if="isLoggedIn" to="/logs" value="logs">
        <v-icon>mdi-clipboard-text-clock</v-icon>
        <span>日志记录</span>
      </v-btn>
      <v-btn v-if="isLoggedIn && userStore.admin_type === 'organization_admin'" to="/reviews" value="reviews">
        <v-icon>mdi-gavel</v-icon>
        <span>人工审核</span>
      </v-btn>
      <v-btn v-if="isLoggedIn" @click="handleLogout" value="logout">
        <v-icon>mdi-logout</v-icon>
        <span>退出登录</span>
      </v-btn>
      <v-btn v-else @click="goToLogin" value="login">
        <v-icon>mdi-login</v-icon>
        <span>登录</span>
      </v-btn>
    </v-bottom-navigation>

    <!-- 通知抽屉 -->
    <v-navigation-drawer v-model="showNotifications" temporary location="right" width="400">
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h5 font-weight-bold">通知</span>
        <v-btn icon @click="showNotifications = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <!-- 通知列表 -->
      <v-list>
        <v-list-item v-for="(notification, index) in notifications" :key="index" :title="notification.title"
          :subtitle="notification.content" :prepend-icon="notification.icon"
          :color="notification.unread ? 'primary' : ''" @click="markAsRead(index)">
          <template v-slot:append>
            <v-chip v-if="notification.unread" color="primary" size="small">
              未读
            </v-chip>
          </template>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <!-- 广播编辑弹窗 -->
    <v-dialog v-model="showBroadcastDialog" max-width="1000">
      <v-card>
        <v-card-title class="text-h5 font-weight-bold">发送广播</v-card-title>
        <v-card-text>
          <v-text-field v-model="broadcastTitle" label="标题" placeholder="请输入广播标题（不超过15字）" 
            variant="outlined" class="mb-4" hide-details counter="15"
            :error="broadcastTitle.length > 15"
            :error-messages="broadcastTitle.length > 15 ? '标题不能超过15字' : ''"></v-text-field>
          <v-row align="stretch" style="height: 400px;">
            <v-col cols="6" class="d-flex flex-column h-100">
              <v-textarea v-model="broadcastContent" label="广播内容" 
                placeholder="输入要广播的内容（支持Markdown格式，不超过400字）"
                variant="outlined" hide-details @input="updatePreview" counter="400"
                :error="broadcastContent.length > 400"
                :error-messages="broadcastContent.length > 400 ? '内容不能超过400字' : ''"
                style="flex: 1 1 auto; min-height: 0; max-height: 100%;"></v-textarea>
            </v-col>
            <v-col cols="6" class="d-flex flex-column h-100">
              <div class="preview-content pa-4" v-html="previewContent"
                style="flex: 1 1 auto; min-height: 0; max-height: 100%; overflow: auto;"></div>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="showBroadcastDialog = false">取消</v-btn>
          <v-btn color="primary" @click="sendBroadcast" 
            :disabled="!broadcastTitle || !broadcastContent || broadcastTitle.length > 15 || broadcastContent.length > 100">
            发送
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-app>
</template>

<script lang="ts" setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { marked } from 'marked'
import { useThemeStore } from '@/stores/theme'

const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

const drawer = ref(true)
const rail = ref(true)
const themeStore = useThemeStore()
const theme = computed(() => themeStore.theme)
const showNotifications = ref(false)
const hasUnreadNotifications = ref(false)
const router = useRouter()

import { isLoggedIn } from './api/user'

import user from '@/api/user'
import Snackbar from '@/components/Snackbar.vue'
import { useUserStore } from '@/stores/user';
const userStore = useUserStore();

import { useSnackbarStore } from '@/stores/snackbar';
import notification from './api/notification'
const snackbar = useSnackbarStore();

// 通知相关
const notifications = ref([
  {
    title: '系统通知',
    content: '欢迎使用学术图像检测系统',
    icon: 'mdi-bell',
    unread: true,
    time: new Date()
  }
])

const broadcastContent = ref('')
const broadcastTitle = ref('')
const showBroadcastDialog = ref(false)
const previewContent = ref('')

// 标记通知为已读
const markAsRead = (index: number) => {
  notifications.value[index].unread = false
  updateUnreadStatus()
}

const getSubTitle = (admin_type : string) =>{
  if(admin_type === 'software_admin'){
    return '软件管理员'
  }else if(admin_type === 'organization_admin'){
    return '组织管理员'
  }
}

// 更新未读状态
const updateUnreadStatus = () => {
  hasUnreadNotifications.value = notifications.value.some(n => n.unread)
}

// 更新预览内容
const updatePreview = async () => {
  previewContent.value = await marked.parse(broadcastContent.value)
}

// 发送广播
const sendBroadcast = async () => {
  if (!broadcastTitle.value || !broadcastContent.value) return
  try {
    const newNotification = {
      title: broadcastTitle.value,
      content: await marked.parse(broadcastContent.value),
      icon: 'mdi-broadcast',
      unread: true,
      time: new Date()
    }
    notifications.value.unshift(newNotification)
    broadcastTitle.value = ''
    broadcastContent.value = ''
    previewContent.value = ''
    showBroadcastDialog.value = false
    updateUnreadStatus()
    await notification.sendBroadcast(newNotification)
    snackbar.showMessage('广播发送成功', 'success')
  } catch (error) {
    snackbar.showMessage('广播发送失败', 'error')
  }
}

const goToHome = () => {
  router.push('/')
}

const goToLogin = () => {
  router.push('/login')
}

const handleLogout = async () => {
  try {
    //localStorage.clear()
    let refresh = localStorage.getItem("1-refresh")
    const response = await user.logout({ refresh })
    localStorage.removeItem("1-refresh")
    localStorage.removeItem("1-token")
    isLoggedIn.value = false
    localStorage.setItem("1-isLoggedIn", "false")
    userStore.clearUserInfo() // 清除用户信息
    snackbar.showMessage('退出成功', 'success')
    router.push('/login')
  } catch (error: any) {
    snackbar.showMessage('请联系管理员', 'error')
  }
}

const toggleTheme = () => {
  themeStore.toggleTheme()
}

const goToAnalytics = () => {
  router.push('/analytics')
}

const goToFiles = () => {
  router.push('/files')
}

const goToOrganizations = () => {
  router.push('/organizations')
}

const goToUsers = () => {
  router.push('/users')
}

const goToLogs = () => {
  router.push('/logs')
}

const goToReviews = () => {
  router.push('/reviews')
}

const goToOrganizationProfile = () => {
  router.push('/organization_profile')
}

onMounted(async () => {
  // 从本地存储加载主题设置
  const savedTheme = localStorage.getItem('app_theme')
  if (savedTheme) {
    themeStore.setTheme(savedTheme)
  }

  // 如果已登录，获取用户信息
  if (isLoggedIn.value) {
    await userStore.fetchUserInfo();
  }
})
</script>

<style>
.v-navigation-drawer__content {
  overflow-y: auto;
}

.navigation-drawer {
  position: fixed !important;
  z-index: 1000;
  transition: all 0.3s ease-in-out !important;
  background-color: rgb(var(--v-theme-surface)) !important;
}

/* 移除主内容区域的左边距 */
.v-main {
  margin-left: 0 !important;
  padding-left: 56px !important;
}

/* 确保导航栏展开时不会影响主内容区域 */
.v-navigation-drawer--rail {
  position: fixed !important;
  z-index: 1000;
}

.v-navigation-drawer--rail:not(:hover) {
  width: 56px !important;
}

.v-navigation-drawer--rail:hover {
  width: 200px !important;
}

/* 固定顶部栏 */
.app-bar {
  position: fixed !important;
  z-index: 1001 !important;
  width: 100% !important;
  left: 0 !important;
  right: 0 !important;
}

/* 调整主内容区域的上边距，为固定顶部栏留出空间 */
.v-main {
  padding-top: 64px !important;
}

.preview-content {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  min-height: 200px;
  background-color: rgb(var(--v-theme-surface));
}
</style>
