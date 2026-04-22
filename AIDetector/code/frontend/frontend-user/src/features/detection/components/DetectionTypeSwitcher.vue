<template>
  <v-card class="mb-6" variant="outlined">
    <v-card-title class="text-h6">AI 检测类型</v-card-title>
    <v-card-text>
      <v-btn-toggle :model-value="modelValue" mandatory class="d-flex flex-wrap ga-2 type-toggle" @update:model-value="emit('update:modelValue', $event)">
        <v-btn value="image" class="type-btn">学术图像检测</v-btn>
        <v-btn value="paper" class="type-btn">全文论文检测</v-btn>
        <v-btn value="review" class="type-btn">同行评审 Review 检测</v-btn>
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
}
</style>
