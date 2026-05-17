<template>
  <v-card class="upload-card">
    <v-card-title class="d-flex align-center text-h6">
      <v-icon color="teal" class="mr-2">mdi-file-document-edit-outline</v-icon>
      全文论文上传
    </v-card-title>
    <v-card-subtitle>上传后可预览文本，并在提交检测前修订提取结果。</v-card-subtitle>
    <v-card-text>
      <div class="upload-area pa-8" @dragover.prevent @drop.prevent="handleDrop" @click="triggerInput">
        <v-icon size="68" color="teal">mdi-file-document-outline</v-icon>
        <div class="text-h6 mt-4">点击或拖拽论文文件到此处上传</div>
        <div class="text-caption text-medium-emphasis">支持 DOCX / PDF / ZIP，单文件不超过 100MB。</div>
        <input ref="inputRef" type="file" accept=".docx,.pdf,.zip" style="display: none" @change="handleSelect">
      </div>

      <v-card v-if="file" variant="outlined" class="mt-4">
        <v-card-text class="d-flex align-center">
          <v-icon color="primary" class="mr-2">mdi-file-document</v-icon>
          <div class="flex-grow-1">
            <div class="text-body-2">{{ displayName || file.name }}</div>
            <div class="text-caption text-grey">
              {{ formatFileSize(displaySize ?? file.size) }}
            </div>
            <div v-if="displayHint" class="text-caption text-primary">{{ displayHint }}</div>
          </div>
          <v-btn icon="mdi-close" variant="text" @click="emit('clear')" />
        </v-card-text>
      </v-card>

      <v-progress-linear v-if="uploading" class="mt-6" :model-value="uploadProgress" height="18" color="primary" rounded>
        <template #default>
          <span class="text-caption text-white">上传中 {{ Math.round(uploadProgress) }}%</span>
        </template>
      </v-progress-linear>
    </v-card-text>

    <v-card-actions class="px-6 pb-6">
      <v-spacer />
      <v-btn color="primary" size="large" :loading="uploading" @click="emit('submit')">
        提交上传
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  file: File | null
  uploading: boolean
  uploadProgress: number
  displayName?: string
  displaySize?: number
  displayHint?: string
}>()

const emit = defineEmits<{
  (e: 'select', file: File): void
  (e: 'clear'): void
  (e: 'submit'): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)

const triggerInput = () => inputRef.value?.click()

const handleSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) emit('select', file)
  target.value = ''
}

const handleDrop = (event: DragEvent) => {
  const file = event.dataTransfer?.files?.[0]
  if (file) emit('select', file)
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}
</script>

<style scoped>
.upload-area {
  border: 2px dashed rgba(15, 159, 122, 0.35);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
  background:
    linear-gradient(145deg, rgba(255,255,255,0.82), rgba(240,247,245,0.78));
}

.upload-area:hover {
  border-color: rgb(var(--v-theme-primary));
  transform: translateY(-2px);
  background-color: rgba(var(--v-theme-primary), 0.06);
}

.upload-card {
  overflow: hidden;
}
</style>
