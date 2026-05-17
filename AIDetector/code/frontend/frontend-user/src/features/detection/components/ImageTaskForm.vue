<template>
  <v-card class="upload-card">
    <v-card-title class="d-flex align-center text-h6">
      <v-icon color="primary" class="mr-2">mdi-image-search-outline</v-icon>
      学术图像上传
    </v-card-title>
    <v-card-subtitle>上传图片、PDF 或 ZIP，系统会帮你提取可检测图像。</v-card-subtitle>
    <v-card-text>
      <div class="upload-area pa-8" @dragover.prevent @drop.prevent="handleDrop" @click="triggerInput">
        <v-icon size="68" color="primary">mdi-cloud-upload-outline</v-icon>
        <div class="text-h6 mt-4">点击或拖拽文件到此处上传</div>
        <div class="text-caption text-medium-emphasis">支持 PNG / JPG / JPEG / PDF / ZIP，单文件不超过 100MB。</div>
        <input ref="inputRef" type="file" multiple accept=".png,.jpg,.jpeg,.pdf,.zip" style="display: none" @change="handleSelect">
      </div>

      <v-list v-if="files.length" class="mt-4" lines="two">
        <v-list-item v-for="(file, idx) in files" :key="`${file.name}-${idx}`">
          <template #prepend>
            <v-icon color="primary">mdi-file</v-icon>
          </template>
          <v-list-item-title>{{ file.name }}</v-list-item-title>
          <v-list-item-subtitle>{{ formatFileSize(file.size) }}</v-list-item-subtitle>
          <template #append>
            <v-btn icon="mdi-close" variant="text" @click.stop="emit('remove', idx)" />
          </template>
        </v-list-item>
      </v-list>

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
  files: File[]
  uploading: boolean
  uploadProgress: number
}>()

const emit = defineEmits<{
  (e: 'select', files: File[]): void
  (e: 'remove', index: number): void
  (e: 'submit'): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)

const triggerInput = () => inputRef.value?.click()

const handleSelect = (event: Event) => {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  if (files.length) emit('select', files)
}

const handleDrop = (event: DragEvent) => {
  const files = Array.from(event.dataTransfer?.files || [])
  if (files.length) emit('select', files)
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
