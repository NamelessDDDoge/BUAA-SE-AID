<template>
  <v-card class="mb-6 type-card">
    <v-card-title class="d-flex align-center text-h6">
      <v-icon color="primary" class="mr-2">mdi-shape-outline</v-icon>
      选择检测类型
    </v-card-title>
    <v-card-subtitle>不同任务会进入不同的预览和确认流程。</v-card-subtitle>
    <v-card-text>
      <v-btn-toggle :model-value="modelValue" mandatory class="d-flex flex-wrap ga-2 type-toggle" @update:model-value="emit('update:modelValue', $event)">
        <v-btn value="image" class="type-btn" rounded="lg">
          <v-icon start>mdi-image-search-outline</v-icon>
          学术图像
        </v-btn>
        <v-btn value="paper" class="type-btn" rounded="lg">
          <v-icon start>mdi-file-document-edit-outline</v-icon>
          全文论文
        </v-btn>
        <v-btn value="review" class="type-btn" rounded="lg">
          <v-icon start>mdi-comment-text-multiple-outline</v-icon>
          Review 检测
        </v-btn>
      </v-btn-toggle>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import type { DetectionType } from '../types'

defineProps<{
  modelValue: DetectionType
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: DetectionType): void
}>()
</script>

<style scoped>
.type-toggle {
  width: 100%;
}

.type-btn {
  flex: 1 1 220px;
  min-height: 52px;
  font-weight: 800;
}

.type-card {
  overflow: hidden;
}
</style>
