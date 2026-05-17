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
        <div class="text-caption text-medium-emphasis">支持 DOCX / PDF / ZIP，可一次选择多个文件，单文件不超过 100MB。</div>
        <input ref="inputRef" type="file" accept=".docx,.pdf,.zip" multiple style="display: none" @change="handleSelect">
      </div>

      <v-card v-if="files.length" variant="outlined" class="mt-4">
        <v-card-text>
          <div class="text-subtitle-2 mb-3">已选择 {{ files.length }} 份论文文件</div>
          <v-list density="compact" lines="two">
            <v-list-item v-for="(selectedFile, idx) in files" :key="`${selectedFile.name}_${idx}`">
              <template #prepend>
                <v-icon color="primary" class="mr-2">mdi-file-document</v-icon>
              </template>
              <v-list-item-title>{{ idx === 0 ? (displayName || selectedFile.name) : selectedFile.name }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatFileSize(idx === 0 && displaySize ? displaySize : selectedFile.size) }}
                <template v-if="idx === 0 && displayHint"> · {{ displayHint }}</template>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
          <div class="d-flex justify-end mt-2">
            <v-btn icon="mdi-close" variant="text" @click="emit('clear')" />
          </div>
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
  files: File[]
  uploading: boolean
  uploadProgress: number
  displayName?: string
  displaySize?: number
  displayHint?: string
}>()

const emit = defineEmits<{
  (e: 'select', files: File[]): void
  (e: 'clear'): void
  (e: 'submit'): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)

const triggerInput = () => inputRef.value?.click()

const handleSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])
  if (files.length) emit('select', files)
  target.value = ''
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
