<template>
    <div class="login-page">
      <!-- 左侧功能介绍区域 -->
      <div class="feature-section">
        <div class="feature-content">
          <div class="feature-kicker">AID Admin</div>
          <h1 class="feature-title">检测管理端</h1>
          <p class="feature-copy">用于组织、用户、资源、模型与人工审核流程管理。</p>
          <div class="feature-list">
            <div class="feature-item">
              <div class="feature-icon">
                <v-icon size="26" color="primary">mdi-view-dashboard-outline</v-icon>
              </div>
              <div class="feature-text">
                <div class="text-subtitle-1 font-weight-bold">平台总览</div>
                <div class="text-body-2 text-grey">集中查看任务、组织和资源状态。</div>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <v-icon size="26" color="primary">mdi-account-cog-outline</v-icon>
              </div>
              <div class="feature-text">
                <div class="text-subtitle-1 font-weight-bold">权限管理</div>
                <div class="text-body-2 text-grey">管理用户、组织与系统角色。</div>
              </div>
            </div>
            <div class="feature-item">
              <div class="feature-icon">
                <v-icon size="26" color="primary">mdi-robot-outline</v-icon>
              </div>
              <div class="feature-text">
                <div class="text-subtitle-1 font-weight-bold">模型配置</div>
                <div class="text-body-2 text-grey">维护检测模型与服务配置。</div>
              </div>
            </div>
          </div>
        </div>
      </div>
  
      <!-- 右侧登录区域 -->
      <div class="login-section">
        <div class="login-container">
          <v-form ref="form" @submit.prevent="handleSubmit">
            <v-text-field
              v-model="email"
              label="请输入邮箱"
              variant="outlined"
              density="comfortable"
              class="mb-4"
              prepend-inner-icon="mdi-email"
              :rules="loginRules.email"
            ></v-text-field>
  
            <v-text-field
              v-model="password"
              label="输入密码"
              variant="outlined"
              density="comfortable"
              class="mb-4"
              type="password"
              prepend-inner-icon="mdi-lock"
              :rules="loginRules.password"
            ></v-text-field>
  
            <!-- 验证码区域 -->
            <div class="captcha-section mb-6">
              <v-text-field
                v-model="captchaInput"
                label="请输入验证码"
                variant="outlined"
                density="comfortable"
                :error-messages="captchaError"
                class="captcha-input"
                prepend-inner-icon="mdi-shield-check"
              >
                <template v-slot:append>
                  <DynamicCaptcha
                    ref="captchaRef"
                    @update:code="code => captchaCode = code"
                  />
                </template>
              </v-text-field>
            </div>
  
            <v-checkbox
              v-model="agreement"
              label="我已阅读《隐私政策》和《使用协议》"
              hide-details
              class="mb-6"
            ></v-checkbox>
  
            <v-btn
              block
              color="primary"
              size="large"
              type="submit"
              :disabled="!isFormValid"
            >
              登录
            </v-btn>
          </v-form>
        </div>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref, computed } from 'vue'
  import { useRouter } from 'vue-router'
  import DynamicCaptcha from '@/components/DynamicCaptcha.vue'
  import { useSnackbarStore } from '@/stores/snackbar';
  const snackbar = useSnackbarStore();
  import user from '@/api/user'
  import { useUserStore } from '@/stores/user';
  const userStore = useUserStore();
  
  const router = useRouter()
  const captchaRef = ref()
  const email = ref('')
  const password = ref('')
  const agreement = ref(false)
  const form = ref(null)
  
  // 验证码相关
  const captchaInput = ref('')
  const captchaCode = ref('')
  const captchaError = ref('')
  
  // 表单验证规则
  const loginRules = {
    email: [
      (v: string) => !!v || '邮箱不能为空',
      // (v: string) => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址'
    ],
    password: [
      (v: string) => !!v || '密码不能为空',
      // (v: string) => v.length >= 6 || '密码至少6个字符'
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
    
    // return email.value && password.value && 
    //        /.+@.+\..+/.test(email.value) && 
    //        password.value.length >= 6
    return email.value && password.value 
  })
  
  const handleSubmit = async () => {
    if (!validateCaptcha()) {
      return
    }
    // localStorage.setItem("isLoggedIn", "true")
    // return

    const response = await user.login({
      email: email.value,
      password: password.value,
      // role: 'admin'//TODO：admin
    }).then(async (res: { data: { access: string; refresh: string } }) => {
      localStorage.setItem("1-token", res.data.access)
      localStorage.setItem("1-refresh", res.data.refresh)
      localStorage.setItem("1-isLoggedIn", "true")
      
      // 获取用户信息并存储到 user store
      await userStore.fetchUserInfo();
      
      snackbar.showMessage('登录成功', 'success')
      router.push('/')
    }).catch((error: { response?: { status: number } }) => {
      console.log(error)
      let errorMessage = '网络错误，请稍后重试'
      if (error.response) {
        switch (error.response.status) {
          case 401:
            errorMessage = '账号/密码错误'
            break
          default://400
            errorMessage = '账号/密码错误'
            break
        }
      }
      snackbar.showMessage(errorMessage, 'error')
    })
  }
  </script>
  
  <style scoped>
  .login-page {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 500px;
    min-height: 100vh;
    padding: 0;
    background:
      radial-gradient(circle at 10% 12%, rgba(47, 111, 237, 0.16), transparent 28rem),
      radial-gradient(circle at 88% 10%, rgba(13, 148, 136, 0.14), transparent 26rem),
      linear-gradient(135deg, #f4f8ff 0%, #f8fbff 48%, #eef5ff 100%);
    gap: 0;
    align-items: stretch;
    justify-content: stretch;
  }
  
  .feature-section {
    min-height: 100vh;
    padding: clamp(56px, 7vw, 108px);
    display: flex;
    align-items: center;
    justify-content: flex-start;
    background:
      linear-gradient(135deg, rgba(255, 255, 255, 0.88), rgba(236, 244, 255, 0.76)),
      radial-gradient(circle at 18% 20%, rgba(47, 111, 237, 0.18), transparent 24rem);
    border-right: 1px solid rgba(23, 32, 51, 0.08);
  }
  
  .feature-content {
    max-width: 720px;
    margin-top: 0;
  }
  
  .feature-kicker {
    color: rgb(var(--v-theme-primary));
    font-size: 0.78rem;
    font-weight: 900;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 12px;
  }

  .feature-title {
    font-size: clamp(2.35rem, 4.2vw, 4.2rem);
    line-height: 1.08;
    font-weight: 900;
    letter-spacing: -0.06em;
    margin-bottom: 18px;
  }

  .feature-copy {
    max-width: 560px;
    color: #667085;
    font-size: 1.12rem;
    line-height: 1.75;
    margin-bottom: 38px;
  }

  .feature-list {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    max-width: 780px;
  }
  
  .feature-item {
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-height: 156px;
    padding: 20px;
    border: 1px solid rgba(23, 32, 51, 0.08);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.72);
    box-shadow: 0 14px 36px rgba(23, 32, 51, 0.06);
  }
  
  .feature-icon {
    padding: 12px;
    background: #eef4ff;
    border-radius: 12px;
    border: 1px solid rgba(47, 111, 237, 0.12);
  }
  
  .feature-text {
    flex: 1;
  }
  
  .login-section {
    width: 500px;
    min-height: 100vh;
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 56px;
    border-left: 1px solid rgba(23, 32, 51, 0.08);
    box-shadow: -24px 0 60px rgba(23, 32, 51, 0.08);
  }
  
  .login-container {
    width: 100%;
    max-width: 420px;
    background: #ffffff;
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
      display: flex;
      flex-direction: column;
      padding: 18px;
      align-items: stretch;
    }
  
    .feature-section {
      min-height: auto;
      padding: 24px;
      border-right: 0;
      border-radius: 22px;
    }
  
    .feature-content {
      margin-top: 0;
    }
  
    .login-section {
      width: 100%;
      min-height: auto;
      min-width: 0;
      max-width: none;
      margin-top: 0;
      padding: 24px;
      border-left: 0;
      border-radius: 22px;
    }
  
    .feature-list {
      grid-template-columns: 1fr;
    }
  }
  </style> 
