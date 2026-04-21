<template>
  <div class="forgot-password-container">
    <v-btn
      icon
      variant="text"
      @click="$emit('close')"
      size="small"
      class="close-button"
    >
      <v-icon size="20">mdi-close</v-icon>
    </v-btn>

    <!-- 顶部标题区域 -->
    <h1 class="text-h4 font-weight-bold mb-12" style="color: rgb(var(--v-theme-on-surface))">找回密码</h1>

    <!-- 步骤指示器 -->
    <v-stepper v-model="currentStep" class="mb-8 stepper-custom">
      <v-stepper-header>
        <v-stepper-item 
          value="1" 
          title="验证身份"
          :complete="currentStep > 1"
        >
          <template v-slot:icon>
            <v-icon color="primary">mdi-account-check</v-icon>
          </template>
        </v-stepper-item>
        <v-divider></v-divider>
        <v-stepper-item 
          value="2" 
          title="重置密码"
          :complete="currentStep > 2"
        >
          <template v-slot:icon>
            <v-icon color="primary">mdi-lock-reset</v-icon>
          </template>
        </v-stepper-item>
        <v-divider></v-divider>
        <v-stepper-item 
          value="3" 
          title="完成"
        >
          <template v-slot:icon>
            <v-icon color="primary">mdi-check-circle</v-icon>
          </template>
        </v-stepper-item>
      </v-stepper-header>
    </v-stepper>

    <!-- 表单区域 -->
    <v-form @submit.prevent="handleSubmit" class="form-container">
      <!-- 步骤1：验证身份 -->
      <template v-if="currentStep === 1">
        <v-text-field
          v-model="form.email"
          label="邮箱地址"
          variant="outlined"
          density="comfortable"
          class="mb-4"
          prepend-inner-icon="mdi-email"
          bg-color="white"
          :rules="[v => !!v || '邮箱不能为空', v => /.+@.+\..+/.test(v) || '请输入有效的邮箱地址']"
        ></v-text-field>

        <div class="verification-section mb-6">
          <v-text-field
            v-model="form.verificationCode"
            label="验证码"
            variant="outlined"
            density="comfortable"
            class="verification-input"
            prepend-inner-icon="mdi-shield-check"
            bg-color="white"
          >
            <template v-slot:append>
              <v-btn
                variant="text"
                :disabled="!!countdown"
                @click="sendVerificationCode"
                class="verification-btn"
                color="primary"
              >
                {{ countdown ? `${countdown}秒后重试` : '获取验证码' }}
              </v-btn>
            </template>
          </v-text-field>
        </div>
      </template>

      <!-- 步骤2：重置密码 -->
      <template v-if="currentStep === 2">
        <v-text-field
          v-model="form.newPassword"
          label="新密码"
          variant="outlined"
          density="comfortable"
          class="mb-4"
          type="password"
          prepend-inner-icon="mdi-lock"
          bg-color="white"
          :rules="[v => !!v || '密码不能为空', v => v.length >= 6 || '密码至少6个字符']"
        ></v-text-field>

        <v-text-field
          v-model="form.confirmPassword"
          label="确认新密码"
          variant="outlined"
          density="comfortable"
          class="mb-6"
          type="password"
          prepend-inner-icon="mdi-lock-check"
          bg-color="white"
          :rules="[v => !!v || '请确认密码', v => v === form.newPassword || '两次输入的密码不一致']"
        ></v-text-field>
      </template>

      <!-- 步骤3：完成 -->
      <template v-if="currentStep === 3">
        <div class="success-message text-center pa-8">
          <v-icon
            color="success"
            size="64"
            class="mb-4"
          >mdi-check-circle</v-icon>
          <div class="text-h6 mb-2">密码重置成功</div>
          <div class="text-body-1 text-grey mb-6">您的密码已经重置成功，请使用新密码登录</div>
        </div>
      </template>

      <!-- 底部按钮 -->
      <template v-if="currentStep !== 3">
        <v-btn
          block
          color="primary"
          size="large"
          type="submit"
          class="mt-4"
        >
          {{ currentStep === 1 ? '下一步' : '确认修改' }}
        </v-btn>
      </template>
      <template v-else>
        <v-btn
          block
          color="primary"
          size="large"
          @click="$emit('close')"
          class="mt-4"
        >
          返回登录
        </v-btn>
      </template>
    </v-form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits(['close'])

const currentStep = ref(1)
const countdown = ref(0)

const form = ref({
  email: '',
  verificationCode: '',
  newPassword: '',
  confirmPassword: ''
})

// 发送验证码
const sendVerificationCode = () => {
  // 这里添加发送验证码的逻辑
  countdown.value = 60
  const timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
    }
  }, 1000)
}

// 处理表单提交
const handleSubmit = () => {
  if (currentStep.value === 1) {
    // 验证邮箱和验证码
    // 验证成功后进入下一步
    currentStep.value = 2
  } else if (currentStep.value === 2) {
    // 验证并提交新密码
    // 提交成功后进入完成步骤
    currentStep.value = 3
  }
}
</script>

<style scoped>
.forgot-password-container {
  width: 100%;
  max-width: 480px;
  background-color: rgb(var(--v-theme-surface));
  padding: 32px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  position: relative;
  margin: 0 auto;
}

.close-button {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 1;
}

.form-container {
  max-width: 400px;
  margin: 0 auto;
}

:deep(.stepper-custom) {
  background-color: transparent !important;
  box-shadow: none !important;
}

:deep(.v-stepper-header) {
  box-shadow: none !important;
  border-radius: 8px;
  background-color: rgba(var(--v-theme-on-surface), 0.05) !important;
  padding: 4px;
}

:deep(.v-stepper-item) {
  padding: 16px 24px;
}

:deep(.v-stepper-item--active) {
  color: rgb(var(--v-theme-primary)) !important;
  
  .v-stepper-item__icon {
    background-color: rgba(var(--v-theme-primary), 0.12) !important;
  }
}

:deep(.v-stepper-item--complete) {
  color: rgb(var(--v-theme-primary)) !important;
}

:deep(.v-stepper-item__title) {
  text-align: center;
  font-size: 14px !important;
  font-weight: 500;
  color: rgb(var(--v-theme-on-surface));
}

:deep(.v-stepper-item .v-icon) {
  color: rgb(var(--v-theme-primary)) !important;
}

.verification-section {
  position: relative;
}

.verification-input {
  width: 100%;
}

.verification-btn {
  min-width: 100px;
  font-weight: 500;
}

:deep(.v-field) {
  background-color: rgb(var(--v-theme-surface)) !important;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
}

:deep(.v-field__input) {
  color: rgb(var(--v-theme-on-surface)) !important;
  font-size: 14px;
}

:deep(.v-label) {
  color: rgba(var(--v-theme-on-surface), 0.6) !important;
  font-size: 14px;
}

:deep(.v-field__outline) {
  border-color: rgba(var(--v-theme-on-surface), 0.12) !important;
}

:deep(.v-field--focused) {
  border-color: rgb(var(--v-theme-primary)) !important;
}

:deep(.v-icon) {
  color: rgba(var(--v-theme-on-surface), 0.54);
}

:deep(.v-btn--icon) {
  color: rgba(var(--v-theme-on-surface), 0.54);
}

:deep(.text-grey) {
  color: rgba(var(--v-theme-on-surface), 0.6) !important;
}
</style> 