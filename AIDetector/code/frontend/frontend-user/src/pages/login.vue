<template>
  <div class="login-page">
    <section class="feature-section" aria-label="平台介绍">
      <div class="brand-shell">
        <div class="brand-topline">
          <div class="brand-mark">
            <v-icon size="24">mdi-shield-search</v-icon>
          </div>
          <span>{{ APP_NAME }}</span>
        </div>

        <div class="feature-content">
          <div class="feature-kicker">Academic Integrity</div>
          <h1 class="feature-title">{{ APP_NAME }}</h1>
          <p class="feature-copy">面向论文、Review 与学术图像的综合检测、复核和报告工作台。</p>
        </div>

        <div class="flow-card" aria-label="检测流程">
          <div class="flow-step">
            <v-icon size="20">mdi-cloud-upload-outline</v-icon>
            <span>上传材料</span>
          </div>
          <div class="flow-line"></div>
          <div class="flow-step">
            <v-icon size="20">mdi-radar</v-icon>
            <span>AI 初筛</span>
          </div>
          <div class="flow-line"></div>
          <div class="flow-step">
            <v-icon size="20">mdi-account-check-outline</v-icon>
            <span>复核归档</span>
          </div>
        </div>

        <div class="brand-footnote">
          <span class="footnote-dot"></span>
          <span>统一管理检测历史、人工审核和报告查阅。</span>
        </div>
      </div>
    </section>

    <section class="login-section" aria-label="账号登录">
      <div class="login-container">
        <div class="login-heading">
          <div class="login-kicker">{{ loginType === 'login' ? 'Sign in' : 'Create account' }}</div>
          <h2>{{ loginType === 'login' ? '欢迎回来' : '创建账号' }}</h2>
        </div>

        <div class="login-tabs mb-8">
          <v-btn-toggle v-model="loginType" mandatory divided class="login-toggle">
            <v-btn value="login" class="flex-grow-1" :class="{ 'active-tab': loginType === 'login' }">登录</v-btn>
            <v-btn value="register" class="flex-grow-1" :class="{ 'active-tab': loginType === 'register' }">注册</v-btn>
          </v-btn-toggle>
        </div>

        <div class="role-selector mb-8">
          <v-btn-toggle v-model="selectedRole" mandatory class="role-toggle">
            <v-btn value="publisher" :class="{ 'active-role': selectedRole === 'publisher' }"
              class="role-btn">编辑</v-btn>
            <v-btn value="reviewer" :class="{ 'active-role': selectedRole === 'reviewer' }" class="role-btn">专家</v-btn>
          </v-btn-toggle>
        </div>

        <v-form ref="form" @submit.prevent="handleSubmit">
          <!-- 登录表单 -->
          <template v-if="loginType === 'login'">
            <v-text-field v-model="email" label="请输入邮箱" variant="outlined" density="comfortable" class="mb-4"
              prepend-inner-icon="mdi-email" :rules="loginRules.email"></v-text-field>

            <v-text-field v-model="password" label="输入密码" variant="outlined" density="comfortable" class="mb-4"
              type="password" prepend-inner-icon="mdi-lock" :rules="loginRules.password"></v-text-field>

            <!-- 验证码区域 -->
            <div class="captcha-section mb-6">
              <v-text-field v-model="captchaInput" label="请输入验证码" variant="outlined" density="comfortable"
                :error-messages="captchaError" class="captcha-input" prepend-inner-icon="mdi-shield-check">
                <template v-slot:append>
                  <DynamicCaptcha ref="captchaRef" @update:code="code => captchaCode = code" />
                </template>
              </v-text-field>
            </div>

            <v-checkbox v-model="agreement" label="我已阅读《隐私政策》和《使用协议》" hide-details class="mb-6"></v-checkbox>
          </template>

          <!-- 注册表单 -->
          <template v-else>
            <v-text-field v-model="registerFormData.username" label="请输入用户名" variant="outlined" density="comfortable"
              class="mb-4" prepend-inner-icon="mdi-account" :rules="[(v: string) => !!v || '用户名不能为空']"
              required></v-text-field>

            <v-text-field v-model="registerFormData.email" label="请输入邮箱" variant="outlined" density="comfortable"
              class="mb-4" prepend-inner-icon="mdi-email"
              :rules="[(v: string) => !!v || '邮箱不能为空', (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址']"
              required></v-text-field>

            <v-text-field v-model="registerFormData.password" label="请输入密码" variant="outlined" density="comfortable"
              class="mb-4" type="password" prepend-inner-icon="mdi-lock"
              :rules="[(v: string) => !!v || '密码不能为空', (v: string) => v.length >= 6 || '密码长度不能少于6位']"
              required></v-text-field>

            <v-text-field v-model="registerFormData.confirmPassword" label="请确认密码" variant="outlined"
              density="comfortable" class="mb-4" type="password" prepend-inner-icon="mdi-lock-check" :rules="[
                (v: string) => !!v || '请确认密码',
                (v: string) => v === registerFormData.password || '两次输入的密码不一致'
              ]" required></v-text-field>

            <v-text-field v-model="registerFormData.inviteCode" label="请输入邀请码" variant="outlined" density="comfortable"
              class="mb-4" prepend-inner-icon="mdi-key" :rules="[(v: string) => !!v || '邀请码不能为空']"
              required></v-text-field>

            <!-- 验证码区域 -->
            <div class="captcha-section mb-6">
              <v-text-field v-model="captchaInput" label="请输入验证码" variant="outlined" density="comfortable"
                :error-messages="captchaError" class="captcha-input" prepend-inner-icon="mdi-shield-check">
                <template v-slot:append>
                  <DynamicCaptcha ref="captchaRef" @update:code="code => captchaCode = code" />
                </template>
              </v-text-field>
            </div>

            <v-checkbox v-model="agreement" label="我已阅读《隐私政策》和《使用协议》" hide-details class="mb-6"></v-checkbox>

            <!-- 创建组织按钮 -->
            <v-btn v-if="selectedRole === 'publisher'" block color="secondary" size="large" class="mb-4"
              @click="showCreateOrgDialog = true">
              创建组织
            </v-btn>
          </template>

          <v-btn block color="primary" size="large" type="submit" :loading="submitting" :disabled="submitting">
            {{ loginType === 'login' ? '登录' : '注册' }}
          </v-btn>

          <div class="text-body-2 text-grey text-center mt-4">
            <template v-if="loginType === 'login'">
              <a href="#" class="text-decoration-none" @click.prevent="showForgotPasswordDialog = true">忘记密码？</a>
            </template>
            <template v-else>
              <span>已有账号？</span>
              <a href="#" class="text-decoration-none ml-1" @click.prevent="loginType = 'login'">立即登录</a>
            </template>
          </div>
        </v-form>
      </div>
    </section>

    <!-- 忘记密码对话框 -->
    <v-dialog v-model="showForgotPasswordDialog" max-width="500" persistent>
      <v-card>
        <v-card-title>重置密码</v-card-title>
        <v-card-text>
          <v-form>
            <div class="d-flex align-center mb-4">
              <v-text-field v-model="forgotPasswordForm.email" label="邮箱" variant="outlined" class="flex-grow-1" :rules="[
                v => !!v || '邮箱不能为空',
                v => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
              ]"></v-text-field>
              <v-btn color="primary" class="ml-2" @click="requestResetEmail" :loading="sendingEmail"
                :disabled="countdown > 0">
                {{ countdown > 0 ? `${countdown}秒后重发` : '发送验证码' }}
              </v-btn>
            </div>

            <div class="mb-4">
              <div class="text-subtitle-2 mb-2">验证码</div>
              <VerificationCodeInput v-model="forgotPasswordForm.verificationCode" />
            </div>

            <v-text-field v-model="forgotPasswordForm.newPassword" label="新密码" type="password" variant="outlined"
              class="mb-4" placeholder="请输入新密码" :rules="[
                v => !!v || '密码不能为空',
                v => v.length >= 6 || '密码至少6个字符'
              ]"></v-text-field>

            <v-text-field v-model="forgotPasswordForm.confirmPassword" label="确认新密码" type="password" variant="outlined"
              class="mb-4" placeholder="请再次输入新密码" :rules="[
                v => !!v || '请确认密码',
                v => v === forgotPasswordForm.newPassword || '两次输入的密码不一致'
              ]"></v-text-field>

            <v-btn color="primary" block @click="resetPassword" :loading="resettingPassword"
              :disabled="!isPasswordResetValid">
              重置密码
            </v-btn>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closeForgotPasswordDialog">
            取消
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 创建组织对话框 -->
    <v-dialog v-model="showCreateOrgDialog" max-width="700" persistent>
      <v-card class="create-org-dialog">
        <v-card-title class="d-flex align-center pa-6">
          <v-icon size="32" color="primary" class="mr-3">mdi-office-building</v-icon>
          <span class="text-h5">创建组织</span>
        </v-card-title>

        <v-card-text class="pa-6">
          <v-form ref="orgForm" @submit.prevent="handleCreateOrg">
            <!-- 组织信息部分 -->
            <div class="form-section mb-8">
              <div class="section-header d-flex align-center mb-4">
                <v-icon color="primary" class="mr-2">mdi-domain</v-icon>
                <span class="text-h6">组织信息</span>
              </div>

              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field v-model="orgFormData.name" label="组织名称" variant="outlined" density="comfortable"
                    :rules="orgRules.name" prepend-inner-icon="mdi-tag"></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model="orgFormData.adminUsername" label="管理员用户名" variant="outlined"
                    density="comfortable" :rules="orgRules.adminUsername"
                    prepend-inner-icon="mdi-account"></v-text-field>
                </v-col>
              </v-row>

              <v-textarea v-model="orgFormData.description" label="组织描述" variant="outlined" density="comfortable"
                :rules="orgRules.description" rows="3" prepend-inner-icon="mdi-text-box"></v-textarea>

              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field v-model="orgFormData.adminEmail" label="管理员邮箱" variant="outlined" density="comfortable"
                    :rules="orgRules.adminEmail" prepend-inner-icon="mdi-email"></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field v-model="orgFormData.adminPassword" label="管理员密码" type="password" variant="outlined"
                    density="comfortable" :rules="orgRules.adminPassword" prepend-inner-icon="mdi-lock"></v-text-field>
                </v-col>
              </v-row>

              <v-text-field v-model="orgFormData.adminConfirmPassword" label="确认管理员密码" type="password"
                variant="outlined" density="comfortable" :rules="orgRules.adminConfirmPassword"
                prepend-inner-icon="mdi-lock-check"></v-text-field>
            </div>

            <!-- 文件上传部分 -->
            <div class="form-section">
              <div class="section-header d-flex align-center mb-4">
                <v-icon color="primary" class="mr-2">mdi-file-upload</v-icon>
                <span class="text-h6">文件上传</span>
              </div>

              <v-row>
                <v-col cols="12" md="6">
                  <div class="upload-section pa-4 rounded-lg">
                    <div class="text-subtitle-2 mb-2">组织Logo</div>
                    <v-file-input v-model="orgFormData.logo" accept="image/*" label="上传Logo" variant="outlined"
                      density="comfortable" prepend-icon="mdi-camera" :rules="orgRules.logo" @change="handleLogoChange"
                      class="mb-2"></v-file-input>
                    <v-img v-if="orgFormData.logoPreview" :src="orgFormData.logoPreview" max-height="150"
                      class="rounded-lg" contain></v-img>
                  </div>
                </v-col>

                <v-col cols="12" md="6">
                  <div class="upload-section pa-4 rounded-lg">
                    <div class="text-subtitle-2 mb-2">证明材料</div>
                    <v-file-input v-model="orgFormData.certificate" accept=".pdf,.jpg,.jpeg,.png" label="上传证明材料"
                      variant="outlined" density="comfortable" prepend-icon="mdi-file-document"
                      :rules="orgRules.certificate"></v-file-input>
                  </div>
                </v-col>
              </v-row>
            </div>
          </v-form>
        </v-card-text>

        <v-divider></v-divider>

        <v-card-actions class="pa-6">
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closeCreateOrgDialog" class="mr-2">
            取消
          </v-btn>
          <v-btn color="primary" variant="elevated" @click="handleCreateOrg" :loading="creatingOrg"
            :disabled="!isOrgFormValid">
            <v-icon start>mdi-check</v-icon>
            创建组织
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import DynamicCaptcha from '@/components/DynamicCaptcha.vue'
import ForgotPassword from '@/components/ForgotPassword.vue'
import { APP_NAME } from '@/constants/app'
import { useSnackbarStore } from '@/stores/snackbar';
const snackbar = useSnackbarStore();
import user from '@/api/user'
import { useUserStore } from '@/stores/user';
const userStore = useUserStore();
import VerificationCodeInput from '@/components/VerificationCodeInput.vue'

const router = useRouter()
const captchaRef = ref()
const loginType = ref('login')
const selectedRole = ref('reviewer')
const email = ref('')
const password = ref('')
const agreement = ref(false)
const showForgotPasswordDialog = ref(false)
const showCreateOrgDialog = ref(false)
const creatingOrg = ref(false)
const submitting = ref(false)
const form = ref(null)
const orgForm = ref(null)

// 注册表单数据
const registerFormData = ref({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  inviteCode: ''
})

// 组织表单数据
const orgFormData = ref({
  name: '',
  description: '',
  logo: null as File | null,
  logoPreview: '',
  certificate: null as File | null,
  adminUsername: '',
  adminEmail: '',
  adminPassword: '',
  adminConfirmPassword: ''
})

// 验证码相关
const captchaInput = ref('')
const captchaCode = ref('')
const captchaError = ref('')

// 表单验证规则
const loginRules = {
  email: [
    (v: string) => !!v || '邮箱不能为空',
    (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
  ],
  password: [
    (v: string) => !!v || '密码不能为空',
    (v: string) => v.length >= 6 || '密码至少6个字符'
  ]
}

const registerRules = {
  email: [
    (v: string) => !!v || '邮箱不能为空',
    (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
  ],
  inviteCode: [
    (v: string) => !!v || '邀请码不能为空',
    (v: string) => v.length >= 6 || '邀请码格式不正确'
  ]
}

const orgRules = {
  name: [
    (v: string) => !!v || '组织名称不能为空',
    (v: string) => v.length >= 2 || '组织名称至少2个字符'
  ],
  description: [
    (v: string) => !!v || '组织描述不能为空',
    (v: string) => v.length >= 10 || '组织描述至少10个字符'
  ],
  logo: [
    (v: File | null) => !!v || '请上传组织Logo',
    (v: File | null) => !v || v.size <= 5 * 1024 * 1024 || 'Logo大小不能超过5MB'
  ],
  certificate: [
    (v: File | null) => !!v || '请上传证明材料',
    (v: File | null) => !v || v.size <= 10 * 1024 * 1024 || '文件大小不能超过10MB'
  ],
  email: [
    (v: string) => !!v || '组织邮箱不能为空',
    (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
  ],
  adminUsername: [
    (v: string) => !!v || '管理员用户名不能为空',
    (v: string) => v.length >= 2 || '用户名至少2个字符'
  ],
  adminEmail: [
    (v: string) => !!v || '管理员邮箱不能为空',
    (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
  ],
  adminPassword: [
    (v: string) => !!v || '管理员密码不能为空',
    (v: string) => v.length >= 6 || '密码至少6个字符'
  ],
  adminConfirmPassword: [
    (v: string) => !!v || '请确认管理员密码',
    (v: string) => v === orgFormData.value.adminPassword || '两次输入的密码不一致'
  ]
}

const validateCaptcha = () => {
  if (!captchaInput.value) {
    captchaError.value = '请输入验证码'
    return false
  }
  if (captchaInput.value.toLowerCase() !== captchaCode.value.toLowerCase()) {
    captchaError.value = '验证码错误'
    captchaInput.value = ''
    captchaRef.value?.refreshCaptcha()
    return false
  }
  captchaError.value = ''
  return true
}

const isFormValid = computed(() => {
  if (!agreement.value) return false
  if (!captchaInput.value) return false

  if (loginType.value === 'login') {
    return email.value && password.value &&
      /.+@.+\..+/.test(email.value) &&
      password.value.length >= 6
  } else {
    return registerFormData.value.email &&
      registerFormData.value.inviteCode &&
      /.+@.+\..+/.test(registerFormData.value.email) &&
      registerFormData.value.inviteCode.length >= 6
  }
})

const getValidationMessage = () => {
  if (loginType.value === 'login') {
    if (!email.value) return '请输入邮箱'
    if (!/.+@.+\..+/.test(email.value)) return '请输入有效的邮箱地址'
    if (!password.value) return '请输入密码'
    if (password.value.length < 6) return '密码至少6个字符'
  } else {
    if (!registerFormData.value.username) return '请输入用户名'
    if (!registerFormData.value.email) return '请输入邮箱'
    if (!/.+@.+\..+/.test(registerFormData.value.email)) return '请输入有效的邮箱地址'
    if (!registerFormData.value.password) return '请输入密码'
    if (registerFormData.value.password.length < 6) return '密码长度不能少于6位'
    if (!registerFormData.value.confirmPassword) return '请确认密码'
    if (registerFormData.value.confirmPassword !== registerFormData.value.password) return '两次输入的密码不一致'
    if (!registerFormData.value.inviteCode) return '请输入邀请码'
    if (registerFormData.value.inviteCode.length < 6) return '邀请码格式不正确'
  }

  if (!captchaInput.value) return '请输入验证码'
  if (!agreement.value) return '请先勾选隐私政策和使用协议'
  return ''
}

const handleSubmit = async () => {
  const validationMessage = getValidationMessage()
  if (validationMessage) {
    snackbar.showMessage(validationMessage, 'error')
    return
  }

  if (!validateCaptcha()) {
    snackbar.showMessage(captchaError.value || '验证码错误', 'error')
    return
  }

  if (submitting.value) return
  submitting.value = true

  try {
    if (loginType.value === 'login') {
      const res = await user.login({
        email: email.value,
        password: password.value,
        role: selectedRole.value
      })

      localStorage.setItem("2-token", res.data.access)
      localStorage.setItem("2-refresh", res.data.refresh)
      localStorage.setItem("2-isLoggedIn", "true")

      snackbar.showMessage('登录成功', 'success')
      await router.push(selectedRole.value === 'reviewer' ? '/review' : '/history')

      void userStore.fetchUserInfo().then((loaded) => {
        if (!loaded) {
          snackbar.showMessage('用户信息加载失败，部分菜单可能暂时不可用', 'warning')
        }
      })
    } else {
      await user.register({
        username: registerFormData.value.username,
        email: registerFormData.value.email,
        password: registerFormData.value.password,
        role: selectedRole.value,
        invitation_code: registerFormData.value.inviteCode
      })
      snackbar.showMessage('注册成功', 'success')
      loginType.value = 'login'
    }
  } catch (error: any) {
    if (loginType.value === 'login') {
      console.log(error)
      let errorMessage = '网络错误，请稍后重试'
      if (error.response) {
        switch (error.response.status) {
          case 401:
            errorMessage = '账号/密码错误'
            break
          default://400
            errorMessage = '请联系管理员'
            break
        }
      }
      snackbar.showMessage(errorMessage, 'error')
    } else {
      let errorMessage = '注册失败，请稍后重试'
      if (error.response) {
        if (error.response.status === 400) {
          // 处理字段验证错误
          const errors = error.response.data
          const errorMessages = []

          if (errors.email) errorMessages.push(`邮箱已存在`)
          if (errors.inviteCode) errorMessages.push(`邀请码已存在`)

          errorMessage = errorMessages.length > 0 ? errorMessages.join(';') : '请检查输入信息'
        }
      }
      snackbar.showMessage(errorMessage, 'error')
    }
  } finally {
    submitting.value = false
  }
}

const forgotPasswordForm = ref({
  email: '',
  verificationCode: '',
  newPassword: '',
  confirmPassword: ''
})

const sendingEmail = ref(false)
const resettingPassword = ref(false)
const countdown = ref(0)
const countdownTimer = ref<number | null>(null)

// 密码重置表单验证
const isPasswordResetValid = computed(() => {
  return forgotPasswordForm.value.email &&
    /.+@.+\..+/.test(forgotPasswordForm.value.email) &&
    forgotPasswordForm.value.verificationCode &&
    forgotPasswordForm.value.newPassword &&
    forgotPasswordForm.value.newPassword === forgotPasswordForm.value.confirmPassword &&
    forgotPasswordForm.value.newPassword.length >= 6
})

// 关闭忘记密码对话框
const closeForgotPasswordDialog = () => {
  showForgotPasswordDialog.value = false
  // 重置表单
  setTimeout(() => {
    forgotPasswordForm.value = {
      email: '',
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
    await user.requestPasswordReset(forgotPasswordForm.value.email)
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
  if (!isPasswordResetValid.value) {
    snackbar.showMessage('请确保两次输入的密码一致且长度不少于6位', 'error')
    return
  }

  try {
    resettingPassword.value = true
    await user.confirmPasswordReset({
      email: forgotPasswordForm.value.email,
      reset_code: forgotPasswordForm.value.verificationCode,
      new_password: forgotPasswordForm.value.newPassword
    })
    snackbar.showMessage('密码重置成功', 'success')
    closeForgotPasswordDialog()
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

// 处理Logo预览
const handleLogoChange = (file: File | null) => {
  if (file && file instanceof File) {
    try {
      const reader = new FileReader()
      reader.onload = (e) => {
        if (e.target?.result) {
          orgFormData.value.logoPreview = e.target.result as string
        }
      }
      reader.onerror = () => {
        console.error('读取文件失败')
        orgFormData.value.logoPreview = ''
        snackbar.showMessage('读取文件失败，请重试', 'error')
      }
      reader.readAsDataURL(file)
    } catch (error) {
      console.error('处理文件时出错:', error)
      orgFormData.value.logoPreview = ''
      snackbar.showMessage('处理文件时出错，请重试', 'error')
    }
  } else {
    orgFormData.value.logoPreview = ''
  }
}

// 关闭创建组织对话框
const closeCreateOrgDialog = () => {
  showCreateOrgDialog.value = false
  // 重置表单
  setTimeout(() => {
    orgFormData.value = {
      name: '',
      description: '',
      logo: null,
      logoPreview: '',
      certificate: null,
      adminUsername: '',
      adminEmail: '',
      adminPassword: '',
      adminConfirmPassword: ''
    }
  }, 300)
}

// 创建组织
const handleCreateOrg = async () => {
  if (!isOrgFormValid.value) return

  try {
    creatingOrg.value = true
    const formData = new FormData()
    formData.append('name', orgFormData.value.name)
    formData.append('description', orgFormData.value.description)
    if (orgFormData.value.logo) {
      formData.append('logo', orgFormData.value.logo)
    }
    if (orgFormData.value.certificate) {
      formData.append('proof_materials', orgFormData.value.certificate)
    }
    formData.append('email', orgFormData.value.adminEmail)
    formData.append('admin_username', orgFormData.value.adminUsername)
    formData.append('admin_email', orgFormData.value.adminEmail)
    formData.append('admin_password', orgFormData.value.adminPassword)

    await user.createOrganization(formData)

    snackbar.showMessage('组织创建成功', 'success')
    closeCreateOrgDialog()
  } catch (error: any) {
    console.error('创建组织失败:', error)
    const errorMsg = error.response?.data?.message || '创建组织失败'
    snackbar.showMessage(errorMsg, 'error')
  } finally {
    creatingOrg.value = false
  }
}

// 组织表单验证
const isOrgFormValid = computed(() => {
  // 检查所有必填字段是否都已填写
  const hasName = orgFormData.value.name && orgFormData.value.name.length >= 2
  const hasDescription = orgFormData.value.description && orgFormData.value.description.length >= 10
  const hasLogo = orgFormData.value.logo !== null
  const hasCertificate = orgFormData.value.certificate !== null
  const hasAdminUsername = orgFormData.value.adminUsername && orgFormData.value.adminUsername.length >= 2
  const hasAdminEmail = orgFormData.value.adminEmail && /.+@.+\..+/.test(orgFormData.value.adminEmail)
  const hasAdminPassword = orgFormData.value.adminPassword && orgFormData.value.adminPassword.length >= 6
  const hasAdminConfirmPassword = orgFormData.value.adminConfirmPassword === orgFormData.value.adminPassword

  // 所有字段都必须填写且符合验证规则
  return hasName && hasDescription && hasLogo && hasCertificate &&
    hasAdminUsername && hasAdminEmail && hasAdminPassword && hasAdminConfirmPassword
})

// 在 script setup 部分添加
const isRegisterFormValid = ref(false)
const registering = ref(false)
</script>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: minmax(420px, 0.9fr) minmax(560px, 1.1fr);
  min-height: 100vh;
  padding: 12px;
  background:
    radial-gradient(circle at 8% 10%, rgba(14, 116, 144, 0.18), transparent 28rem),
    radial-gradient(circle at 92% 8%, rgba(20, 184, 166, 0.16), transparent 30rem),
    linear-gradient(135deg, #e9f5f1 0%, #f7fbf9 46%, #ecf4ff 100%);
  gap: 28px;
  align-items: stretch;
  align-content: center;
  justify-content: stretch;
}

.feature-section {
  max-height: calc(100vh - 24px);
  padding: clamp(28px, 4vw, 56px);
  display: flex;
  align-items: stretch;
  justify-content: stretch;
  background:
    linear-gradient(145deg, rgba(11, 72, 84, 0.94), rgba(19, 118, 105, 0.9)),
    radial-gradient(circle at 20% 12%, rgba(255, 255, 255, 0.16), transparent 22rem);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 28px;
  box-shadow: 0 28px 80px rgba(15, 54, 66, 0.22);
  color: #ffffff;
  overflow: hidden;
  position: relative;
}

.feature-section::before {
  content: "";
  position: absolute;
  inset: auto -20% -18% 8%;
  height: 300px;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.22) 1px, transparent 1px),
    linear-gradient(rgba(255, 255, 255, 0.16) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: linear-gradient(to top, rgba(0, 0, 0, 0.8), transparent);
  opacity: 0.55;
  transform: rotate(-5deg);
}

.brand-shell {
  width: 100%;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 40px;
}

.brand-topline {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brand-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.feature-content {
  max-width: 560px;
}

.feature-kicker {
  color: rgba(204, 251, 241, 0.92);
  font-size: 0.78rem;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.feature-title {
  font-size: clamp(2.05rem, 3.6vw, 3.35rem);
  line-height: 1.12;
  font-weight: 900;
  letter-spacing: -0.04em;
  margin-bottom: 16px;
}

.feature-copy {
  max-width: 500px;
  color: rgba(240, 253, 250, 0.82);
  font-size: 1.05rem;
  line-height: 1.72;
}

.flow-card {
  display: grid;
  grid-template-columns: auto 1fr auto 1fr auto;
  align-items: center;
  gap: 14px;
  max-width: 580px;
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.flow-step {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 700;
  font-size: 0.92rem;
}

.flow-line {
  height: 1px;
  min-width: 48px;
  background: linear-gradient(90deg, rgba(204, 251, 241, 0.65), rgba(204, 251, 241, 0.08));
}

.brand-footnote {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: rgba(240, 253, 250, 0.78);
  font-size: 0.95rem;
}

.footnote-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #5eead4;
  box-shadow: 0 0 0 6px rgba(94, 234, 212, 0.16);
}

.login-section {
  max-height: calc(100vh - 24px);
  overflow-y: auto;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(28px, 4vw, 56px);
  border: 1px solid rgba(21, 34, 56, 0.08);
  border-radius: 28px;
  box-shadow: 0 28px 80px rgba(21, 34, 56, 0.1);
}

.login-container {
  width: 100%;
  max-width: 500px;
  background: #ffffff;
}

.login-heading {
  margin-bottom: 8px;
}

.login-heading h2 {
  font-size: clamp(1.8rem, 2.4vw, 2.35rem);
  line-height: 1.16;
  font-weight: 900;
  letter-spacing: -0.04em;
  color: #102a43;
  margin: 0 0 8px;
}

.login-heading p {
  margin: 0;
  color: #667085;
  line-height: 1.7;
}

.login-kicker {
  color: #0f9f7a;
  font-size: 0.76rem;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.login-toggle {
  width: 100%;
  border: none;
  border-radius: 14px;
  overflow: hidden;
  background: #eef5f2;
  padding: 4px;
}

.login-toggle .v-btn {
  background-color: transparent;
  color: #344054;
  font-weight: 500;
  height: 44px;
  transition: all 0.3s ease;
}

.login-toggle .active-tab {
  background: #ffffff;
  color: #0f9f7a;
  box-shadow: 0 6px 18px rgba(21, 34, 56, 0.1);
}

.role-toggle {
  width: 100%;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border: none;
}

.role-btn {
  flex: 1;
  background: #f6faf8 !important;
  color: #344054 !important;
  border: 1px solid rgba(21, 34, 56, 0.08) !important;
  border-radius: 12px !important;
  transition: all 0.3s ease;
  height: 40px;
  font-weight: 500;
}

.role-btn:hover {
  background: rgba(var(--v-theme-primary), 0.1) !important;
  color: rgb(var(--v-theme-primary)) !important;
}

.active-role {
  background: #0f9f7a !important;
  color: #ffffff !important;
  border: none !important;
}

.v-btn {
  text-transform: none !important;
  background-color: var(--v-theme-primary);
  color: var(--v-theme-on-primary);
}

.v-btn.v-btn--size-large {
  height: 48px;
  font-size: 16px;
  font-weight: 700;
  border-radius: 14px;
  box-shadow: 0 12px 24px rgba(15, 159, 122, 0.18);
  transition: all 0.3s ease;
}

.v-btn.v-btn--size-large:hover {
  background-color: var(--v-theme-primary-light);
  box-shadow: 0 4px 8px rgba(64, 158, 255, 0.3);
  transform: translateY(-1px);
}

.v-btn.v-btn--size-large:active {
  background-color: var(--v-theme-primary-dark);
  transform: translateY(0);
}

.captcha-section {
  width: 100%;
}

.captcha-input {
  width: 100%;
}

/* 收紧白框内表单字段的纵向间距 */
.login-container .v-text-field.mb-4 {
  margin-bottom: 0 !important;
}

/* 按钮（创建组织、注册/登录）保留上下间距 */
.login-container .v-btn--size-large,
.login-container .v-btn.mb-4 {
  margin-top: 10px;
}

.login-container .v-btn.mb-4 {
  margin-bottom: 10px !important;
}

.login-container .mb-6 {
  margin-bottom: 4px !important;
}

.login-container .login-tabs.mb-8,
.login-container .role-selector.mb-8 {
  margin-bottom: 6px !important;
}

.login-container .mt-4 {
  margin-top: 6px !important;
}

/* 收起字段下方预留的提示信息空白 */
.login-container :deep(.v-input__details) {
  min-height: 2px;
  padding-top: 0;
}

/* 压缩“我已阅读……协议”勾选框的高度与上下间距 */
.login-container .v-checkbox {
  margin-top: -12px;
}

.login-container :deep(.v-checkbox .v-selection-control) {
  min-height: 26px;
}

.login-container :deep(.v-checkbox .v-label) {
  font-size: 0.8rem;
  opacity: 0.85;
}

:deep(.v-field__append-inner) {
  padding-top: 6px;
}

@media (max-width: 1024px) {
  .login-page {
    display: flex;
    flex-direction: column;
    padding: 18px;
    align-items: stretch;
  }

  .feature-section {
    min-height: auto;
    padding: 28px;
    border-right: 0;
    border-radius: 22px;
  }

  .brand-shell {
    gap: 28px;
  }

  .login-section {
    min-height: auto;
    min-width: 0;
    max-width: none;
    margin-top: 0;
    padding: 28px;
    border-left: 0;
    border-radius: 22px;
  }

  .flow-card {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .flow-line {
    display: none;
  }
}

.forgot-password-dialog :deep(.v-overlay__content) {
  opacity: 1;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.forgot-password-dialog :deep(.v-overlay__scrim) {
  opacity: 0.7;
  background-color: rgb(var(--v-theme-on-surface));
}

.create-org-dialog {
  border-radius: 12px;
}

.form-section {
  background-color: rgba(var(--v-theme-surface), 0.5);
  border-radius: 8px;
  padding: 20px;
}

.section-header {
  border-bottom: 2px solid rgba(var(--v-theme-primary), 0.1);
  padding-bottom: 8px;
}

.upload-section {
  background-color: rgba(var(--v-theme-surface), 0.8);
  border: 1px dashed rgba(var(--v-theme-primary), 0.2);
  transition: all 0.3s ease;
}

.upload-section:hover {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.05);
}

:deep(.v-field__input) {
  padding-top: 2px;
  padding-bottom: 2px;
}

:deep(.v-field__prepend-inner) {
  padding-top: 8px;
}
</style>
