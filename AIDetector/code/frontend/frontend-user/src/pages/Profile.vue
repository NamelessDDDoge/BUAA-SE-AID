<template>
  <v-container>
    <v-row>
      <v-col cols="12" md="4">
        <!-- 个人信息卡片 -->
        <v-card class="mb-4">
          <v-card-item>
            <div class="d-flex justify-center">
              <v-avatar size="120" class="mb-4 position-relative">
                <v-img :src="userStore.avatar" cover></v-img>
                <v-btn icon="mdi-camera" variant="flat" color="primary" size="small" class="position-absolute"
                  style="bottom: 0; right: 0" @click="triggerFileInput"></v-btn>
              </v-avatar>
            </div>
            <input type="file" ref="fileInput" style="display: none" accept="image/*" @change="handleAvatarChange">
            <v-card-title class="text-center">{{ userStore.displayName }}</v-card-title>
            <v-card-subtitle class="text-center">{{ userStore.userRole }}</v-card-subtitle>
          </v-card-item>
          <v-card-text>
            <v-list>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-email</v-icon>
                </template>
                <v-list-item-title>邮箱</v-list-item-title>
                <v-list-item-subtitle>{{ userStore.email || '未设置' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-account-group</v-icon>
                </template>
                <v-list-item-title>所属组织</v-list-item-title>
                <v-list-item-subtitle>{{ userStore.organization_name || '未加入组织' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-text-box</v-icon>
                </template>
                <v-list-item-title>个人简介</v-list-item-title>
                <v-list-item-subtitle>{{ userStore.profile || '未设置' }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
          <v-card-actions class="justify-center">
            <v-btn color="primary" variant="outlined" prepend-icon="mdi-pencil" @click="showEditDialog = true">
              编辑个人信息
            </v-btn>
            <v-btn color="warning" variant="outlined" prepend-icon="mdi-lock-reset" @click="showPasswordDialog = true">
              修改密码
            </v-btn>
          </v-card-actions>
        </v-card>

        <!-- 统计信息卡片 -->
        <v-card>
          <v-card-title>统计信息</v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-image</v-icon>
                </template>
                <v-list-item-title>已上传任务</v-list-item-title>
                <v-list-item-subtitle>{{ stats.uploadedTasks }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template v-slot:prepend>
                  <v-icon>mdi-check-circle</v-icon>
                </template>
                <v-list-item-title>已完成任务</v-list-item-title>
                <v-list-item-subtitle>{{ stats.completedTasks }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <!-- 最近活动 -->
        <v-card>
          <v-card-title class="d-flex align-center">
            <span>最近活动</span>
            <v-spacer></v-spacer>
            <span class="text-caption text-grey">最近5条记录</span>
          </v-card-title>
          <v-card-text>
            <v-timeline density="compact" align="start" class="activity-timeline">
              <template v-if="recentActivities && recentActivities.length > 0">
                <v-timeline-item v-for="(activity, index) in recentActivities.slice(-5).reverse()" :key="index"
                  :dot-color="getStatusColor(activity.status)" size="small">
                  <div class="d-flex justify-space-between align-center w-100">
                    <div class="activity-info">
                      <div class="text-subtitle-1">{{ activity.task_name }}</div>
                      <div class="text-caption text-grey">{{ formatDateTime(activity.completion_time) }}</div>
                    </div>
                    <v-chip :color="getStatusColor(activity.status)" size="small" class="activity-status">
                      {{ getStatusType(activity.status) }}
                    </v-chip>
                  </div>
                </v-timeline-item>
                <!-- 填充空白项以保持对齐 -->
                <template v-if="recentActivities.length < 5">
                  <v-timeline-item v-for="n in (5 - recentActivities.length)" :key="`empty-${n}`"
                    dot-color="transparent" size="small">
                    <div class="d-flex justify-space-between align-center w-100">
                      <div class="activity-info">
                        <div class="text-subtitle-1 text-grey-lighten-1">-</div>
                        <div class="text-caption text-grey-lighten-1">-</div>
                      </div>
                      <v-chip color="transparent" size="small" class="activity-status">-</v-chip>
                    </div>
                  </v-timeline-item>
                </template>
              </template>
              <div v-else class="text-center py-4">
                <v-icon size="48" color="grey-lighten-1">mdi-information-outline</v-icon>
                <div class="text-subtitle-1 mt-2 text-grey">暂无活动记录</div>
              </div>
            </v-timeline>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 编辑个人信息对话框 -->
    <v-dialog v-model="showEditDialog" max-width="500">
      <v-card>
        <v-card-title>编辑个人信息</v-card-title>
        <v-card-text>
          <v-form>
            <v-text-field v-model="editForm.username" label="用户名" variant="outlined" class="mb-4"
              :rules="[v => !v || v.length <= 10 || '用户名不能超过10个字']" counter="10"></v-text-field>
            <v-text-field v-model="editForm.email" label="邮箱" variant="outlined" class="mb-4" disabled></v-text-field>
            <v-textarea v-model="editForm.profile" label="个人简介" variant="outlined" rows="3"
              :rules="[v => !v || v.length <= 10 || '个人简介不能超过10个字']" counter="10"></v-textarea>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="showEditDialog = false">
            取消
          </v-btn>
          <v-btn color="primary" variant="text" @click="handleUpdateProfile" :loading="updating"
            :disabled="!isEditFormValid">
            保存
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 修改密码对话框 -->
    <v-dialog v-model="showPasswordDialog" max-width="500">
      <v-card>
        <v-card-title>修改密码</v-card-title>
        <v-card-text>
          <v-form>
            <div class="d-flex align-center mb-4">
              <v-text-field v-model="passwordForm.email" label="邮箱" variant="outlined" :value="userStore.email" disabled
                class="flex-grow-1"></v-text-field>
              <v-btn color="primary" class="ml-2" @click="requestResetEmail" :loading="sendingEmail"
                :disabled="countdown > 0">
                {{ countdown > 0 ? `${countdown}秒后重发` : '发送验证码' }}
              </v-btn>
            </div>

            <div class="mb-4">
              <div class="text-subtitle-2 mb-2">验证码</div>
              <VerificationCodeInput v-model="passwordForm.verificationCode" />
            </div>

            <v-text-field v-model="passwordForm.newPassword" label="新密码" type="password" variant="outlined" class="mb-4"
              placeholder="请输入新密码"></v-text-field>

            <v-text-field v-model="passwordForm.confirmPassword" label="确认新密码" type="password" variant="outlined"
              class="mb-4" placeholder="请再次输入新密码"></v-text-field>

            <v-btn color="primary" block @click="resetPassword" :loading="resettingPassword"
              :disabled="!isPasswordValid">
              重置密码
            </v-btn>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closePasswordDialog">
            取消
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script lang="ts" setup>
import { reactive, onMounted, ref, computed, onUnmounted } from 'vue'
import user from '@/api/user'
import { useSnackbarStore } from '@/stores/snackbar'
import { useUserStore } from '@/stores/user'
import { useRoute } from 'vue-router'
import VerificationCodeInput from '@/components/VerificationCodeInput.vue'
import publisher from '@/api/publisher'
import reviewer from '@/api/reviewer'

const snackbar = useSnackbarStore()
const userStore = useUserStore()
const route = useRoute()

// 编辑表单
const showEditDialog = ref(false)
const updating = ref(false)
const editForm = ref({
  username: '',
  email: '',
  profile: '',
  avatar: null as File | null
})

// 密码重置相关
const showPasswordDialog = ref(false)
const sendingEmail = ref(false)
const resettingPassword = ref(false)
const countdown = ref(0)
const countdownTimer = ref<number | null>(null)
const passwordForm = ref({
  email: '',
  verificationCode: '',
  newPassword: '',
  confirmPassword: ''
})


// 密码验证
const isPasswordValid = computed(() => {
  return passwordForm.value.verificationCode &&
    passwordForm.value.newPassword &&
    passwordForm.value.newPassword === passwordForm.value.confirmPassword &&
    passwordForm.value.newPassword.length >= 6
})

// 关闭密码对话框
const closePasswordDialog = () => {
  showPasswordDialog.value = false
  // 重置表单
  setTimeout(() => {
    passwordForm.value = {
      email: userStore.email,
      verificationCode: '',
      newPassword: '',
      confirmPassword: ''
    }
    // 清除倒计时
    if (countdownTimer.value) {
      clearInterval(countdownTimer.value)
      countdownTimer.value = null
    }
    countdown.value = 0
  }, 300)
}

// 开始倒计时
const startCountdown = () => {
  countdown.value = 60
  if (countdownTimer.value) {
    clearInterval(countdownTimer.value)
  }
  countdownTimer.value = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (countdownTimer.value) {
        clearInterval(countdownTimer.value)
        countdownTimer.value = null
      }
    }
  }, 1000)
}

// 请求重置密码邮件
const requestResetEmail = async () => {
  try {
    sendingEmail.value = true
    await user.requestPasswordReset(passwordForm.value.email)
    snackbar.showMessage('验证码已发送，请查收邮箱', 'success')
    startCountdown()
  } catch (error: any) {
    console.error('发送验证码失败:', error)
    const errorMsg = error.response?.data?.message || '发送验证码失败'
    snackbar.showMessage(errorMsg, 'error')
  } finally {
    sendingEmail.value = false
  }
}

// 重置密码
const resetPassword = async () => {
  if (!isPasswordValid.value) {
    snackbar.showMessage('请确保两次输入的密码一致且长度不少于6位', 'error')
    return
  }

  try {
    resettingPassword.value = true
    await user.confirmPasswordReset({
      email: passwordForm.value.email,
      reset_code: passwordForm.value.verificationCode,
      new_password: passwordForm.value.newPassword
    })
    snackbar.showMessage('密码重置成功', 'success')
    closePasswordDialog()
  } catch (error: any) {
    console.error('重置密码失败:', error)
    const errorMsg = '重置密码失败'
    snackbar.showMessage(errorMsg, 'error')
  } finally {
    resettingPassword.value = false
  }
}

// 组件卸载时清除定时器
onUnmounted(() => {
  if (countdownTimer.value) {
    clearInterval(countdownTimer.value)
    countdownTimer.value = null
  }
})

// 文件上传相关
const fileInput = ref<HTMLInputElement | null>(null)

const stats = ref({
  uploadedTasks: 0,
  completedTasks: 0
})

// 在 script setup 部分添加接口定义
interface RecentActivity {
  task_name: string
  completion_time: string
  status: string
  color: string
}

// 修改 recentActivities 的初始化
const recentActivities = ref<RecentActivity[]>([])

// 获取用户信息
onMounted(async () => {
  try {
    await userStore.fetchUserInfo()
    // 初始化编辑表单
    editForm.value = {
      username: userStore.username,
      email: userStore.email,
      profile: userStore.profile,
      avatar: null
    }
    // 初始化密码表单
    passwordForm.value.email = userStore.email
    if (userStore.role === 'publisher') {
      const response = (await publisher.getTaskSummary()).data
      stats.value.completedTasks = response.completed_task_count
      stats.value.uploadedTasks = response.total_task_count
      recentActivities.value = response.recent_tasks
    } else {
      const res = (await reviewer.getTaskCount()).data
      stats.value.completedTasks = res.total_completed_tasks
      stats.value.uploadedTasks = res.total_received_tasks
      recentActivities.value = (await reviewer.getRecentActivities()).data
    }
  } catch (error) {
    console.error('获取用户信息失败:', error)
    snackbar.showMessage('获取用户信息失败', 'error')
  }
})

// 触发文件选择
const triggerFileInput = () => {
  fileInput.value?.click()
}

// 处理头像上传
const handleAvatarChange = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) {
    try {
      // 先预览新头像
      const reader = new FileReader()
      reader.onload = (e) => {
        // 临时更新头像显示
        userStore.avatar = e.target?.result as string
      }
      reader.readAsDataURL(file)

      // 上传头像
      const success = await userStore.updateAvatar(file)
      if (success) {
        snackbar.showMessage('头像更新成功', 'success')
      } else {
        // 如果上传失败，恢复原来的头像
        await userStore.fetchUserInfo()
        snackbar.showMessage('头像更新失败', 'error')
      }
    } catch (error) {
      console.error('更新头像失败:', error)
      // 发生错误时恢复原来的头像
      await userStore.fetchUserInfo()
      snackbar.showMessage('头像上传失败', 'error')
    }
  }
}

// 更新个人信息
const handleUpdateProfile = async () => {
  try {
    updating.value = true
    const formData = new FormData()

    // 添加文本字段
    formData.append('username', editForm.value.username)
    formData.append('email', editForm.value.email)
    formData.append('profile', editForm.value.profile)

    await user.updateUserInfo(formData)

    // 重新获取用户信息以更新 store
    await userStore.fetchUserInfo()

    showEditDialog.value = false
    snackbar.showMessage('个人信息更新成功', 'success')
  } catch (error) {
    console.error('更新个人信息失败:', error)
    snackbar.showMessage('更新个人信息失败', 'error')
  } finally {
    updating.value = false
  }
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'completed':
      return '成功'
    case 'pending':
      return '等待'
    case 'in_progress':
      return '进行中'
    default:
      return '未知'
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'pending':
      return 'info'
    default:
      return 'grey'
  }
}

const isEditFormValid = computed(() => {
  return (!editForm.value.username || editForm.value.username.length <= 10) &&
    (!editForm.value.profile || editForm.value.profile.length <= 10)
})

const formatDateTime = (dateString: string) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

</script>

<style scoped>
.position-relative {
  position: relative;
}

.position-absolute {
  position: absolute;
}

.activity-timeline {
  min-height: 300px;
}

.activity-info {
  min-width: 200px;
}

.activity-status {
  min-width: 80px;
  justify-content: center;
}

.w-100 {
  width: 100%;
}
</style>