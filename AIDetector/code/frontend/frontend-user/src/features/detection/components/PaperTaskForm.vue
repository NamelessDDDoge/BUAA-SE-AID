<template>
  <v-card variant="outlined">
    <v-card-title class="text-h6">全文论文上传</v-card-title>
    <v-card-subtitle>上传论文文件后可进行段落、参考文献和可选的图像分析。</v-card-subtitle>
    <v-card-text>
      <div class="upload-area pa-8" @dragover.prevent @drop.prevent="handleDrop" @click="triggerInput">
        <v-icon size="64" color="grey">mdi-file-document-outline</v-icon>
        <div class="text-h6 mt-4">点击或拖拽论文文件到此处上传</div>
        <div class="text-caption text-grey">支持 DOCX / PDF / ZIP，单文件不超过 100MB。</div>
        <input ref="inputRef" type="file" accept=".docx,.pdf,.zip" style="display: none" @change="handleSelect">
      </div>

      <v-card v-if="file" variant="outlined" class="mt-4">
        <v-card-text class="d-flex align-center">
          <v-icon color="primary" class="mr-2">mdi-file-document</v-icon>
          <div class="flex-grow-1">
            <div class="text-body-2">{{ file.name }}</div>
            <div class="text-caption text-grey">{{ formatFileSize(file.size) }}</div>
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
}>()

const emit = defineEmits<{
  (e: 'select', file: File): void
  (e: 'clear'): void
  (e: 'submit'): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)

const triggerInput = () => inputRef.value?.click()

const handleSelect = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) emit('select', file)
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
  border: 2px dashed #ccc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}

.upload-area:hover {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.05);
}
</style>
