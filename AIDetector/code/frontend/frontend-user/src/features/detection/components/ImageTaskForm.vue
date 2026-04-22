<template>
  <v-card variant="outlined">
    <v-card-title class="text-h6">学术图像上传</v-card-title>
    <v-card-subtitle>支持上传单张图片、PDF 或 ZIP 压缩包进行图像检测。</v-card-subtitle>
    <v-card-text>
      <div class="upload-area pa-8" @dragover.prevent @drop.prevent="handleDrop" @click="triggerInput">
        <v-icon size="64" color="grey">mdi-cloud-upload</v-icon>
        <div class="text-h6 mt-4">点击或拖拽文件到此处上传</div>
        <div class="text-caption text-grey">支持 PNG / JPG / JPEG / PDF / ZIP，单文件不超过 100MB。</div>
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
