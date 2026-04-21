<template>
  <div class="verification-code-input">
    <div class="code-boxes">
      <v-text-field
        v-for="(digit, index) in 6"
        :key="index"
        v-model="codeArray[index]"
        :ref="el => { if (el) inputRefs[index] = el }"
        class="code-box"
        maxlength="1"
        @input="handleInput(index)"
        @keydown="handleKeydown($event, index)"
        @paste="handlePaste"
        variant="outlined"
        density="comfortable"
        hide-details
      ></v-text-field>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { VTextField } from 'vuetify/components'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const codeArray = ref<string[]>(Array(6).fill(''))
const inputRefs = ref<any[]>([])

// 监听外部值变化
watch(() => props.modelValue, (newValue) => {
  if (newValue !== codeArray.value.join('')) {
    codeArray.value = newValue.split('').concat(Array(6).fill('')).slice(0, 6)
  }
}, { immediate: true })

// 处理输入
const handleInput = (index: number) => {
  const value = codeArray.value[index]
  if (value && index < 5) {
    inputRefs.value[index + 1]?.focus()
  }
  emit('update:modelValue', codeArray.value.join(''))
}

// 处理键盘事件
const handleKeydown = (event: KeyboardEvent, index: number) => {
  if (event.key === 'Backspace' && !codeArray.value[index] && index > 0) {
    inputRefs.value[index - 1]?.focus()
  }
}

// 处理粘贴
const handlePaste = (event: ClipboardEvent) => {
  event.preventDefault()
  const pastedData = event.clipboardData?.getData('text').slice(0, 6) || ''
  codeArray.value = pastedData.split('').concat(Array(6).fill('')).slice(0, 6)
  emit('update:modelValue', codeArray.value.join(''))
  if (pastedData.length === 6) {
    inputRefs.value[5]?.focus()
  }
}
</script>

<style scoped>
.verification-code-input {
  width: 100%;
}

.code-boxes {
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.code-box {
  flex: 1;
  max-width: 48px;
}

:deep(.v-field__input) {
  text-align: center;
  font-size: 18px;
  font-weight: 500;
  letter-spacing: 2px;
}

:deep(.v-field__input:focus) {
  background-color: var(--v-theme-primary-light);
}
</style> 