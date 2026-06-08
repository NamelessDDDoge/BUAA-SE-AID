<template>
  <v-app :theme="theme">
    <Snackbar />
    <!-- 只在非移动端显示侧边导航栏 -->
    <aside v-if="!isMobile && !isLoginPage" class="navigation-drawer">
      <div class="brand-block">
        <div class="brand-mark">
          <v-icon size="26">mdi-shield-crown-outline</v-icon>
        </div>
        <div class="brand-copy">
          <div class="brand-title">{{ APP_NAME }}</div>
          <div class="brand-subtitle">检测管理台</div>
        </div>
      </div>

      <v-list>
        <v-list-item :prepend-avatar="isLoggedIn ? userStore.avatar : undefined" :subtitle="getSubTitle(userStore.admin_type)"
          :title="userStore.displayName || '管理员'">
        </v-list-item>
      </v-list>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-home" title="主页" value="home" color="primary" :active="activeSection === 'home'" @click="goToHome"></v-list-item>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-chart-bar" title="统计分析" value="analytics" color="primary" :active="activeSection === 'analytics'"
          @click="goToAnalytics"></v-list-item>
        <v-list-item v-if="isLoggedIn && userStore.admin_type === 'software_admin'" 
          prepend-icon="mdi-office-building" title="组织管理" value="organizations" color="primary" :active="activeSection === 'organizations'"
          @click="goToOrganizations"></v-list-item>
        <v-list-item v-if="isLoggedIn && userStore.admin_type === 'organization_admin'" 
          prepend-icon="mdi-account-circle" title="组织信息" value="organization_profile" color="primary" :active="activeSection === 'organization_profile'"
          @click="goToOrganizationProfile"></v-list-item>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-folder" title="资源管理" value="files" color="primary" :active="activeSection === 'files'"
          @click="goToFiles"></v-list-item>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-account-group" title="用户管理" value="users" color="primary" :active="activeSection === 'users'"
          @click="goToUsers"></v-list-item>
                <v-list-item v-if="isLoggedIn && userStore.admin_type === 'software_admin'" prepend-icon="mdi-robot-outline" title="模型配置" value="llms" color="primary" :active="activeSection === 'llms'"
          @click="goToLLMs"></v-list-item>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-clipboard-text-clock" title="日志记录" value="logs" color="primary" :active="activeSection === 'logs'"
          @click="goToLogs"></v-list-item>
        <v-list-item v-if="isLoggedIn" 
          prepend-icon="mdi-gavel" title="人工审核" value="reviewRequests" color="primary" :active="activeSection === 'reviews'"
          @click="goToReviews"></v-list-item>
        <v-divider class="my-2"></v-divider>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-logout" title="退出登录" value="logout"
          @click="handleLogout"></v-list-item>
        <v-list-item v-else prepend-icon="mdi-login" title="登录" value="login" @click="goToLogin"></v-list-item>
      </v-list>
    </aside>

    <v-app-bar v-if="!isLoginPage" class="app-bar" elevation="0">
      <v-toolbar-title class="toolbar-title">
        <span>{{ APP_NAME }}</span>
      </v-toolbar-title>
      <v-spacer></v-spacer>
      <!-- <v-btn v-if="isAdmin" :color="hasUnreadNotifications ? 'red' : ''"
        :icon="hasUnreadNotifications ? 'mdi-bell-badge' : 'mdi-bell-outline'"
        @click="showNotifications = true"></v-btn> -->
      <v-btn icon="mdi-broadcast" v-if="isLoggedIn && userStore.admin_type === 'software_admin'" @click="showBroadcastDialog = true"></v-btn>
    </v-app-bar>

    <v-main class="main-stage" :class="{ 'auth-stage': isLoginPage }">
      <div class="route-frame" :class="{ 'auth-frame': isLoginPage }">
        <router-view />
      </div>
    </v-main>

    <!-- 移动端底部导航栏 -->
    <v-bottom-navigation v-if="isMobile && !isLoginPage">
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
        <span>资源管理</span>
      </v-btn>
      <v-btn v-if="isLoggedIn" to="/users" value="users">
        <v-icon>mdi-account-group</v-icon>
        <span>用户管理</span>
      </v-btn>
      <v-btn v-if="isLoggedIn" to="/logs" value="logs">
        <v-icon>mdi-clipboard-text-clock</v-icon>
        <span>日志记录</span>
      </v-btn>
      <v-btn v-if="isLoggedIn" to="/reviews" value="reviews">
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
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { marked } from 'marked'
import { useThemeStore } from '@/stores/theme'

const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

const drawer = ref(true)
const themeStore = useThemeStore()
const theme = computed(() => themeStore.theme)
const showNotifications = ref(false)
const hasUnreadNotifications = ref(false)
const router = useRouter()
const route = useRoute()

const normalizePath = (path: string) => path.replace(/\/+$/, '') || '/'
const isLoginPage = computed(() => normalizePath(route.path) === '/login')

const activeSection = computed(() => {
  const path = normalizePath(route.path)
  if (path === '/') return 'home'
  if (path === '/analytics') return 'analytics'
  if (path === '/organizations') return 'organizations'
  if (path === '/organization_profile') return 'organization_profile'
  if (path === '/files') return 'files'
  if (path === '/users') return 'users'
  if (path === '/llms') return 'llms'
  if (path === '/logs') return 'logs'
  if (path === '/reviews') return 'reviews'
  return ''
})

import { isLoggedIn } from './api/user'

import user from '@/api/user'
import Snackbar from '@/components/Snackbar.vue'
import { APP_NAME } from '@/constants/app'
import { useUserStore } from '@/stores/user';
const userStore = useUserStore();

import { useSnackbarStore } from '@/stores/snackbar';
import notification from './api/notification'
const snackbar = useSnackbarStore();

// 通知相关
const notifications = ref([
  {
    title: '系统通知',
    content: `欢迎使用${APP_NAME}`,
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
  router.push(isLoggedIn.value ? '/' : '/login')
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

const goToLLMs = () => {
  router.push('/llms')
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
  themeStore.setTheme('light')

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
  left: 0;
  top: 0;
  bottom: 0;
  width: 248px;
  height: 100vh;
  overflow-y: auto;
  position: fixed !important;
  z-index: 1000;
  transition: all 0.3s ease-in-out !important;
  background-color: rgb(var(--v-theme-surface)) !important;
}

.navigation-drawer .v-list-item--active {
  background: rgba(var(--v-theme-primary), 0.12) !important;
  box-shadow: inset 4px 0 0 rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-primary)) !important;
  font-weight: 800;
}

.navigation-drawer .v-list-item--active .v-icon {
  color: rgb(var(--v-theme-primary)) !important;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 76px;
  padding: 16px 18px 10px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(135deg, #2f6fed, #0d9488);
  box-shadow: 0 12px 26px rgba(47, 111, 237, 0.28);
}

.brand-copy {
  min-width: 0;
}

.brand-title {
  font-size: 0.98rem;
  font-weight: 900;
  letter-spacing: -0.02em;
}

.brand-subtitle {
  font-size: 0.76rem;
  color: rgba(23, 32, 51, 0.58);
}

/* 左侧导航使用固定 aside，主内容只偏移一次。 */
.v-main {
  margin-left: 248px !important;
  padding-left: 0 !important;
}

/* 固定顶部栏 */
.app-bar {
  position: fixed !important;
  z-index: 1001 !important;
  width: calc(100% - 248px) !important;
  left: 248px !important;
  right: 0 !important;
}

.toolbar-title {
  line-height: 1.2;
  font-weight: 900;
}

/* 调整主内容区域的上边距，为固定顶部栏留出空间 */
.v-main {
  padding-top: 64px !important;
}

.main-stage {
  min-height: 100vh;
}

.auth-stage.v-main,
.auth-stage .v-main {
  margin-left: 0 !important;
  padding-top: 0 !important;
  padding-left: 0 !important;
}

.route-frame {
  width: 100%;
  max-width: 1320px;
  margin: 0 auto;
  padding: 18px 24px 28px;
}

.auth-frame {
  min-height: 100vh;
  padding: 0;
}

.route-frame > .v-container {
  width: 100%;
  max-width: none !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
  padding: 0 !important;
}

.route-frame :is(.workspace-shell, .page-shell, .analytics-container) {
  width: 100%;
  max-width: none !important;
  margin-left: 0 !important;
  margin-right: 0 !important;
}

@media (max-width: 960px) {
  .app-bar {
    width: 100% !important;
    left: 0 !important;
  }

  .v-main {
    margin-left: 0 !important;
    padding-left: 0 !important;
    padding-bottom: 72px !important;
  }

  .route-frame {
    padding: 14px;
  }
}

.preview-content {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  min-height: 200px;
  background-color: rgb(var(--v-theme-surface));
}
</style>
