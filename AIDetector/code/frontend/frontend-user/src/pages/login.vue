<template>
  <div class="login-page">
    <!-- 左侧功能介绍区域 -->
    <div class="feature-section">
      <div class="feature-content">
        <h1 class="text-h4 font-weight-bold mb-12">学术图像造假检测平台</h1>
        <div class="feature-grid">
          <div class="feature-item">
            <div class="feature-icon">
              <v-icon size="32" color="primary">mdi-magnify</v-icon>
            </div>
            <div class="feature-text">
              <div class="text-subtitle-1 font-weight-medium">AI精准检测</div>
              <div class="text-body-2 text-grey">基于深度学习与图像分析技术，精准识别重复、篡改、拼接等学术图像异常。</div>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <v-icon size="32" color="primary">mdi-compare</v-icon>
            </div>
            <div class="feature-text">
              <div class="text-subtitle-1 font-weight-medium">秒级快速筛查</div>
              <div class="text-body-2 text-grey">AI预检测可在数秒内完成初筛，大幅降低人工审核成本，提升出版社工作效率</div>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <v-icon size="32" color="primary">mdi-account-group</v-icon>
            </div>
            <div class="feature-text">
              <div class="text-subtitle-1 font-weight-medium">双重验证机制</div>
              <div class="text-body-2 text-grey">AI初检+人工复核双保险，确保结果客观可信，降低误判风险。</div>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <v-icon size="32" color="primary">mdi-pencil</v-icon>
            </div>
            <div class="feature-text">
              <div class="text-subtitle-1 font-weight-medium">多角色协同平台</div>
              <div class="text-body-2 text-grey">支持出版社、审稿人多端登录，任务进度实时追踪，反馈结果集中归档。</div>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <v-icon size="32" color="primary">mdi-school</v-icon>
            </div>
            <div class="feature-text">
              <div class="text-subtitle-1 font-weight-medium">可追溯审计</div>
              <div class="text-body-2 text-grey">所有操作留痕，满足出版机构对流程透明性与合规性的严格要求</div>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-icon">
              <v-icon size="32" color="primary">mdi-chart-bar</v-icon>
            </div>
            <div class="feature-text">
              <div class="text-subtitle-1 font-weight-medium">多维统计分析</div>
              <div class="text-body-2 text-grey">自动生成结构化检测报告，附带篡改区域标记与证据链，助力学术争议裁定。</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧登录区域 -->
    <div class="login-section">
      <div class="login-container">
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

          <v-btn block color="primary" size="large" type="submit" :disabled="!isFormValid">
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
    </div>

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

const handleSubmit = async () => {
  if (!validateCaptcha()) {
    return
  }
  // 继续登录/注册流程...
  if (loginType.value === 'login') {
    const response = await user.login({
      email: email.value,
      password: password.value,
      role: selectedRole.value
    }).then(async res => {
      localStorage.setItem("2-token", res.data.access)
      localStorage.setItem("2-refresh", res.data.refresh)
      localStorage.setItem("2-isLoggedIn", "true")

      // 获取用户信息并存储到 user store
      await userStore.fetchUserInfo();

      snackbar.showMessage('登录成功', 'success')
      router.push('/')
    }).catch(error => {
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
    })
  } else {
    try {
      const response = await user.register({
        username: registerFormData.value.username,
        email: registerFormData.value.email,
        password: registerFormData.value.password,
        role: selectedRole.value,
        invitation_code: registerFormData.value.inviteCode
      })
      snackbar.showMessage('注册成功', 'success')
      loginType.value = 'login'
    } catch (error: any) {
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
  display: flex;
  min-height: 100vh;
  background-color: var(--v-theme-background);
  padding-top: 40px;
}

.feature-section {
  flex: 1;
  padding: 24px 48px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background-color: var(--v-theme-surface);
}

.feature-content {
  max-width: 800px;
  margin-top: -20px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 32px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.feature-icon {
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}

.feature-text {
  flex: 1;
}

.login-section {
  width: 480px;
  background-color: var(--v-theme-surface);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 32px 48px;
  margin-top: -20px;
}

.login-container {
  width: 100%;
  max-width: 360px;
  background-color: var(--v-theme-surface);
}

.login-toggle {
  width: 100%;
  border: none;
  border-radius: 8px;
  overflow: hidden;
  background-color: var(--v-theme-surface);
}

.login-toggle .v-btn {
  background-color: transparent;
  color: var(--v-theme-on-surface);
  font-weight: 500;
  height: 44px;
  transition: all 0.3s ease;
}

.login-toggle .active-tab {
  background-color: var(--v-theme-primary);
  color: var(--v-theme-on-primary);
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
  background-color: var(--v-theme-surface) !important;
  color: var(--v-theme-on-surface) !important;
  border: none !important;
  transition: all 0.3s ease;
  height: 40px;
  font-weight: 500;
}

.role-btn:hover {
  background-color: var(--v-theme-primary-light) !important;
  color: var(--v-theme-on-primary) !important;
}

.active-role {
  background-color: var(--v-theme-primary) !important;
  color: var(--v-theme-on-primary) !important;
  border: none !important;
}

.v-btn {
  text-transform: none !important;
  background-color: var(--v-theme-primary);
  color: var(--v-theme-on-primary);
}

.v-btn.v-btn--size-large {
  height: 44px;
  font-size: 16px;
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.2);
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

:deep(.v-field__append-inner) {
  padding-top: 6px;
}

@media (max-width: 1024px) {
  .login-page {
    flex-direction: column;
    padding-top: 20px;
  }

  .feature-section {
    padding: 24px;
  }

  .feature-content {
    margin-top: 0;
  }

  .login-section {
    width: 100%;
    margin-top: 0;
    padding: 24px;
  }

  .feature-grid {
    grid-template-columns: 1fr;
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
  padding-top: 8px;
  padding-bottom: 8px;
}

:deep(.v-field__prepend-inner) {
  padding-top: 8px;
}
</style>