<template>
    <div class="login-page">
      <section class="feature-section" aria-label="管理端介绍">
        <div class="brand-shell">
          <div class="brand-topline">
            <div class="brand-mark">
              <v-icon size="24">mdi-view-dashboard-outline</v-icon>
            </div>
            <span>AID Admin</span>
          </div>

          <div class="feature-content">
            <div class="feature-kicker">Admin Console</div>
            <h1 class="feature-title">检测管理端</h1>
            <p class="feature-copy">集中处理组织、用户、资源和人工审核流程。</p>
          </div>

          <div class="flow-card" aria-label="管理范围">
            <div class="flow-step">
              <v-icon size="20">mdi-domain</v-icon>
              <span>组织</span>
            </div>
            <div class="flow-line"></div>
            <div class="flow-step">
              <v-icon size="20">mdi-account-group-outline</v-icon>
              <span>用户</span>
            </div>
            <div class="flow-line"></div>
            <div class="flow-step">
              <v-icon size="20">mdi-clipboard-check-outline</v-icon>
              <span>审核</span>
            </div>
          </div>

          <div class="brand-footnote">
            <span class="footnote-dot"></span>
            <span>管理操作请使用已授权账号登录。</span>
          </div>
        </div>
      </section>
  
      <section class="login-section" aria-label="管理员登录">
        <div class="login-container">
          <div class="login-heading">
            <div class="login-kicker">Secure access</div>
            <h2>管理员登录</h2>
            <p>进入后台管理工作台。</p>
          </div>

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
              :loading="submitting"
              :disabled="submitting"
            >
              登录
            </v-btn>
          </v-form>
        </div>
      </section>
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
  const submitting = ref(false)
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

  const getValidationMessage = () => {
    if (!email.value) return '请输入邮箱'
    if (!password.value) return '请输入密码'
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
      const res = await user.login({
        email: email.value,
        password: password.value,
        // role: 'admin'//TODO：admin
      }) as { data: { access: string; refresh: string } }

      localStorage.setItem("1-token", res.data.access)
      localStorage.setItem("1-refresh", res.data.refresh)
      localStorage.setItem("1-isLoggedIn", "true")

      snackbar.showMessage('登录成功', 'success')
      await router.push('/analytics')

      void userStore.fetchUserInfo().then((loaded) => {
        if (!loaded) {
          snackbar.showMessage('管理员信息加载失败，部分菜单可能暂时不可用', 'warning')
        }
      })
    } catch (error: any) {
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
    } finally {
      submitting.value = false
    }
  }
  </script>
  
  <style scoped>
  .login-page {
    display: grid;
    grid-template-columns: minmax(420px, 0.9fr) minmax(560px, 1.1fr);
    min-height: 100vh;
    padding: 28px;
    background:
      radial-gradient(circle at 8% 10%, rgba(37, 99, 235, 0.18), transparent 28rem),
      radial-gradient(circle at 92% 8%, rgba(15, 23, 42, 0.12), transparent 30rem),
      linear-gradient(135deg, #eef4ff 0%, #f8fbff 46%, #eef2f7 100%);
    gap: 28px;
    align-items: stretch;
    justify-content: stretch;
  }
  
  .feature-section {
    min-height: calc(100vh - 56px);
    padding: clamp(34px, 5vw, 72px);
    display: flex;
    align-items: stretch;
    justify-content: stretch;
    background:
      linear-gradient(145deg, rgba(15, 23, 42, 0.96), rgba(30, 64, 175, 0.9)),
      radial-gradient(circle at 20% 12%, rgba(255, 255, 255, 0.14), transparent 22rem);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 28px;
    box-shadow: 0 28px 80px rgba(15, 23, 42, 0.22);
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
      linear-gradient(90deg, rgba(255, 255, 255, 0.18) 1px, transparent 1px),
      linear-gradient(rgba(255, 255, 255, 0.12) 1px, transparent 1px);
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
    max-width: 540px;
  }
  
  .feature-kicker {
    color: rgba(219, 234, 254, 0.92);
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
    color: rgba(239, 246, 255, 0.8);
    font-size: 1.05rem;
    line-height: 1.72;
  }

  .flow-card {
    display: grid;
    grid-template-columns: auto 1fr auto 1fr auto;
    align-items: center;
    gap: 14px;
    max-width: 540px;
    padding: 18px;
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.11);
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
    background: linear-gradient(90deg, rgba(191, 219, 254, 0.65), rgba(191, 219, 254, 0.08));
  }

  .brand-footnote {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    color: rgba(239, 246, 255, 0.74);
    font-size: 0.95rem;
  }

  .footnote-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #93c5fd;
    box-shadow: 0 0 0 6px rgba(147, 197, 253, 0.16);
  }
  
  .login-section {
    min-height: calc(100vh - 56px);
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: clamp(34px, 5vw, 80px);
    border: 1px solid rgba(23, 32, 51, 0.08);
    border-radius: 28px;
    box-shadow: 0 28px 80px rgba(23, 32, 51, 0.1);
  }
  
  .login-container {
    width: 100%;
    max-width: 500px;
    background: #ffffff;
  }

  .login-heading {
    margin-bottom: 32px;
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
    color: #2563eb;
    font-size: 0.76rem;
    font-weight: 900;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 10px;
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
    box-shadow: 0 12px 24px rgba(37, 99, 235, 0.18);
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
  </style> 
