<template>
  <v-app :theme="theme">
    <Snackbar />

    <!-- 只在非移动端显示侧边导航栏 -->
    <v-navigation-drawer v-if="!isMobile" v-model="drawer" :rail="rail" :permanent="true" :temporary="false"
      location="left" class="navigation-drawer" @mouseenter="rail = false" @mouseleave="rail = true"
      :width="rail ? 56 : 200">
      <v-list>
        <v-list-item :prepend-avatar="isLoggedIn ? userStore.avatar : undefined" :subtitle="userStore.role"
          :title="userStore.displayName">
        </v-list-item>
      </v-list>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-home" title="主页" value="home" @click="goToHome"></v-list-item>
        <v-list-item v-if="userStore.role === 'publisher'" prepend-icon="mdi-image" title="上传任务" value="upload"
          @click="goToUpload"></v-list-item>
        <v-list-item v-if="userStore.role === 'publisher'" prepend-icon="mdi-history" title="检测历史" value="history"
          @click="goToHistory"></v-list-item>
        <v-list-item v-if="userStore.role === 'publisher'" prepend-icon="mdi-gavel" title="人工审核" value="annual"
          @click="gotoAnnual"></v-list-item>
        <v-list-item v-if="userStore.role === 'reviewer'" prepend-icon="mdi-book-open-page-variant" title="审阅"
          value="review" @click="goToReview"></v-list-item>
        <v-list-item v-if="isLoggedIn" prepend-icon="mdi-account" title="个人主页" value="profile"
          @click="goToProfile"></v-list-item>
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
      <v-btn v-if="isLoggedIn" :color="hasUnreadNotifications ? 'red' : ''"
        :icon="hasUnreadNotifications ? 'mdi-bell-badge' : 'mdi-bell-outline'" @click="toggleNotification()"></v-btn>
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
      <v-btn v-if="userStore.role === 'publisher'" to="/upload" value="upload">
        <v-icon>mdi-image</v-icon>
        <span>上传任务</span>
      </v-btn>
      <v-btn v-if="userStore.role === 'publisher'" to="/history" value="history">
        <v-icon>mdi-history</v-icon>
        <span>检测历史</span>
      </v-btn>
      <v-btn v-if="userStore.role === 'publisher'" to="/annual" value="annual">
        <v-icon>mdi-gavel</v-icon>
        <span>人工审核</span>
      </v-btn>
      <v-btn v-if="userStore.role === 'reviewer'" to="/review" value="review">
        <v-icon>mdi-book-open-page-variant</v-icon>
        <span>审阅</span>
      </v-btn>
      <v-btn v-if="isLoggedIn" to="/profile" value="profile">
        <v-icon>mdi-account</v-icon>
        <span>个人主页</span>
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

    <v-navigation-drawer v-model="showDrawer" location="right" width="400" temporary>
      <v-toolbar flat>
        <v-toolbar-title class="text-h6">
          <v-icon icon="mdi-bell" start class="me-2"></v-icon>
          通知中心
        </v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" @click="showDrawer = false"></v-btn>
      </v-toolbar>

      <v-divider></v-divider>
      <v-card-actions>
        <v-btn variant="text" prepend-icon="mdi-check-all" @click="markAllAsRead">
          全部标记已读
        </v-btn>
      </v-card-actions>

      <v-card-text class="pa-0" style="overflow-y: auto; max-height: 80vh;">
        <v-list v-if="notifications.length > 0" lines="two" density="comfortable">
          <template v-for="(item, index) in notifications" :key="item.id">
            <v-list-item :class="{ 'bg-blue-lighten-5': item.status !== 'read', 'text-grey': item.status === 'read' }" @click="openDetail(item)">
              <template #prepend>
                <v-chip size="small" :color="getCategoryColor(item.category)" class="me-2" :class="{ 'opacity-50': item.status === 'read' }">
                  {{ getCategoryLabel(item.category) }}
                </v-chip>
              </template>

              <v-list-item-title class="d-flex justify-space-between align-center">
                <span :class="{ 'font-weight-bold': item.status !== 'read', 'text-grey': item.status === 'read' }">
                  {{ item.title }}
                </span>
                <!-- <v-btn variant="text" size="small" @click.stop="openDetail(item)" :class="{ 'text-grey': item.status === 'read' }">
                  详情
                </v-btn> -->
                <v-btn v-if="item.url" :href="getUrl(item.url)" target="_blank" variant="text" size="small"
                  class="text-primary" :class="{ 'text-grey': item.status === 'read' }">
                  跳转
                </v-btn>
              </v-list-item-title>

              <v-list-item-subtitle class="text-truncate text-wrap">
                <div v-html="renderBriefMarkdown(item.content)"></div>
              </v-list-item-subtitle>
            </v-list-item>

            <v-divider v-if="index < notifications.length - 1"></v-divider>
          </template>
        </v-list>

        <v-alert v-else type="info" variant="tonal" class="mt-4" icon="mdi-information">
          暂无新通知
        </v-alert>
      </v-card-text>
    </v-navigation-drawer>

    <!-- 详情弹窗 -->
    <v-dialog v-model="showDetailDialog" max-width="600px">
      <v-card>
        <v-card-title class="text-h6 d-flex align-center">
          <v-icon icon="mdi-information" class="me-2"></v-icon>
          {{ selectedNotification?.title }}
          <v-spacer></v-spacer>
          <v-btn icon="mdi-close" variant="text" @click="showDetailDialog = false"></v-btn>
        </v-card-title>
        <v-divider></v-divider>

        <v-card-text>
          <p class="text-caption text-medium-emphasis">{{ selectedNotification?.notified_at }}</p>
          <div class="mt-2 markdown-body" v-html="renderMarkdown(selectedNotification?.content)"></div>
        </v-card-text>
      </v-card>
    </v-dialog>


  </v-app>
</template>

<script lang="ts" setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { isLoggedIn } from './api/user'
import { marked } from 'marked'


const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)
import user from '@/api/user'
import Snackbar from '@/components/Snackbar.vue'
import { useUserStore } from '@/stores/user';
const userStore = useUserStore();

import { useSnackbarStore } from '@/stores/snackbar';
import notification from './api/notification'
const snackbar = useSnackbarStore();


const drawer = ref(true)
const rail = ref(true)
const theme = ref('light')
const hasUnreadNotifications = ref(false)
const router = useRouter()
const notifications = ref<Notification[]>([])

const showDrawer = ref(false)
const showDetailDialog = ref(false)
const selectedNotification = ref<Notification>()

let timer: number | null

marked.setOptions({
  breaks: true,
  gfm: true
})

const renderMarkdown = (content?: string) => {
  return content ? marked.parse(content) : ''
}

const renderBriefMarkdown = (content?: string) => {
  if (!content) return ''
  const plainText = content.length > 60 ? content.slice(0, 60) + '...' : content
  return marked.parseInline(plainText)
}



interface Notification {
  id: number,
  user_id: string,
  user_name: string,
  category: string,
  title: string,
  content: string,
  status: string,
  url: string,
  notified_at: string,
  expanded: boolean
}

const openDetail = (item: Notification) => {
  selectedNotification.value = item
  showDetailDialog.value = true
  if (item.status !== 'read') {
    markAsRead(item)
    item.status = 'read' // 标记为已读
  }
}


const getUrl = (url: string) => {
  return import.meta.env.VITE_API_URL
}


const getCategoryLabel = (category: string) => {
  switch (category) {
    case 'GLOBAL': return '管理员'
    case 'SYSTEM': return 'AI检测'
    case 'P2R': return '出版社'
    case 'R2P': return '审稿人'
    default: return '未知'
  }
}

const getCategoryColor = (category: string) => {
  switch (category) {
    case 'GLOBAL': return 'red'
    case 'SYSTEM': return 'blue'
    case 'P2R': return 'green'
    case 'R2P': return 'purple'
    default: return 'grey'
  }
}


const toggleNotification = () => {
  fetchNotification()
  showDrawer.value = true
}

const markAsRead = async (item: Notification) => {
  try {
    await notification.setSingleRead({ notification_id: item.id })
  } catch (error) {
    snackbar.showMessage('标记已读失败', 'error')
  }
}


const goToHome = () => {
  router.push('/')
}

const goToUpload = () => {
  router.push('/upload')
}

const goToHistory = () => {
  router.push('/history')
}

const gotoAnnual = () => {
  router.push('/annual')
}

const goToReview = () => {
  router.push('/review')
}

const goToLogin = () => {
  router.push('/login')
}

const handleLogout = async () => {
  try {
    //localStorage.clear()
    let refresh = localStorage.getItem("2-refresh")
    const response = await user.logout({ refresh })
    localStorage.removeItem("2-refresh")
    localStorage.removeItem("2-token")
    isLoggedIn.value = false
    localStorage.setItem("2-isLoggedIn", "false")
    userStore.clearUserInfo() // 清除用户信息
    snackbar.showMessage('退出成功', 'success')
    router.push('/login')
  } catch (error: any) {
    snackbar.showMessage('请联系管理员', 'error')
  }
}

const toggleTheme = () => {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  localStorage.setItem('app_theme', theme.value)
}

const goToProfile = () => {
  router.push('/profile')
}

const fetchUnRead = async () => {
  try {
    const res = (await notification.getUnRead()).data
    if (res.not_read > 0) {
      hasUnreadNotifications.value = true
    } else {
      hasUnreadNotifications.value = false
    }
  } catch (error) {
    snackbar.showMessage('获取未读通知失败', 'error')
  }
}

const fetchNotification = async () => {
  try {
    const res = (await notification.getAllNotifications()).data
    notifications.value = res.notifications.map((item: Notification) => ({
      ...item,
      expanded: false,
    }))
    console.log(notifications.value)
  } catch (error) {
    snackbar.showMessage('获取所有通知失败')
  }
}

const markAllAsRead = async () => {
  try {
    await notification.setReadAll()
    hasUnreadNotifications.value = false
    fetchNotification()
  } catch (error) {
    snackbar.showMessage('标记全部已读失败')
  }
}


onMounted(async () => {
  // 从本地存储加载主题设置
  const savedTheme = localStorage.getItem('app_theme')
  if (savedTheme) {
    theme.value = savedTheme
  }

  // 如果已登录，获取用户信息
  if (isLoggedIn.value) {
    await userStore.fetchUserInfo();
    fetchUnRead()
    timer = window.setInterval(fetchUnRead, 60000)
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
</style>
