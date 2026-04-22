<template>
  <v-card variant="outlined">
    <v-card-title class="text-h6">Review 检测上传</v-card-title>
    <v-card-subtitle>请同时上传原论文与对应的 Review 文件。</v-card-subtitle>
    <v-card-text>
      <v-row>
        <v-col cols="12" md="6">
          <div class="text-subtitle-1 mb-2">1. 上传原论文</div>
          <div class="upload-area pa-6" @dragover.prevent @drop.prevent="handlePaperDrop" @click="triggerPaperInput">
            <v-icon size="44" color="grey">mdi-file-document-outline</v-icon>
            <div class="text-body-1 mt-2">点击或拖拽论文文件</div>
            <div class="text-caption text-grey">支持 DOCX / PDF / ZIP，单文件不超过 100MB。</div>
            <input ref="paperInputRef" type="file" accept=".docx,.pdf,.zip" style="display: none" @change="handlePaperSelect">
          </div>

          <v-card v-if="paperFile" variant="outlined" class="mt-3">
            <v-card-text class="d-flex align-center">
              <v-icon color="primary" class="mr-2">mdi-file-document</v-icon>
              <div class="flex-grow-1">
                <div class="text-body-2">{{ paperFile.name }}</div>
                <div class="text-caption text-grey">{{ formatFileSize(paperFile.size) }}</div>
              </div>
              <v-btn icon="mdi-close" variant="text" @click="emit('clear-paper')" />
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <div class="text-subtitle-1 mb-2">2. 上传对应 Review 文件</div>
          <div class="upload-area pa-6" @dragover.prevent @drop.prevent="handleReviewDrop" @click="triggerReviewInput">
            <v-icon size="44" color="grey">mdi-comment-text-outline</v-icon>
            <div class="text-body-1 mt-2">点击或拖拽 Review 文件</div>
            <div class="text-caption text-grey">支持 DOCX / PDF / TXT / ZIP，单文件不超过 100MB。</div>
            <input ref="reviewInputRef" type="file" accept=".docx,.pdf,.txt,.zip" style="display: none" @change="handleReviewSelect">
          </div>

          <v-card v-if="reviewFile" variant="outlined" class="mt-3">
            <v-card-text class="d-flex align-center">
              <v-icon color="primary" class="mr-2">mdi-file-document-edit-outline</v-icon>
              <div class="flex-grow-1">
                <div class="text-body-2">{{ reviewFile.name }}</div>
                <div class="text-caption text-grey">{{ formatFileSize(reviewFile.size) }}</div>
              </div>
              <v-btn icon="mdi-close" variant="text" @click="emit('clear-review')" />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

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
  paperFile: File | null
  reviewFile: File | null
  uploading: boolean
  uploadProgress: number
}>()

const emit = defineEmits<{
  (e: 'select-paper', file: File): void
  (e: 'select-review', file: File): void
  (e: 'clear-paper'): void
  (e: 'clear-review'): void
  (e: 'submit'): void
}>()

const paperInputRef = ref<HTMLInputElement | null>(null)
const reviewInputRef = ref<HTMLInputElement | null>(null)

const triggerPaperInput = () => paperInputRef.value?.click()
const triggerReviewInput = () => reviewInputRef.value?.click()

const handlePaperSelect = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) emit('select-paper', file)
}

const handleReviewSelect = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) emit('select-review', file)
}

const handlePaperDrop = (event: DragEvent) => {
  const file = event.dataTransfer?.files?.[0]
  if (file) emit('select-paper', file)
}

const handleReviewDrop = (event: DragEvent) => {
  const file = event.dataTransfer?.files?.[0]
  if (file) emit('select-review', file)
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
