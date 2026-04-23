<template>
  <div class="d-flex flex-column ga-4">
    <ResourceDetectionDetailStep :task="task" :reviewer-options="reviewerOptions" @download="emit('download')" @request-review="emit('request-review', $event)" />
    
    <!-- 论文段落检测结果展示 -->
    <v-card v-if="task?.results?.paragraph_results?.length" class="mt-4" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="primary">mdi-text-box-search-outline</v-icon>
        <span class="text-h6">论文段落检测结果</span>
      </v-card-title>
      <v-card-text>
        <v-list lines="three">
          <v-list-item v-for="(para, index) in task.results.paragraph_results" :key="index" class="mb-4 pa-4 bg-grey-lighten-4 rounded-lg">
            <template #prepend>
              <v-avatar :color="para.label === 'suspicious' ? 'error' : 'success'" size="40" class="mr-4 text-white">
                {{ para.paragraph_index + 1 }}
              </v-avatar>
            </template>
            <v-list-item-title class="text-subtitle-1 font-weight-bold mb-2">
              检测结果: {{ para.label === 'suspicious' ? '疑似 AI 生成' : '正常' }} 
              <v-chip size="small" :color="para.label === 'suspicious' ? 'error' : 'success'" class="ml-2">
                概率: {{ (para.probability * 100).toFixed(1) }}%
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle class="text-body-1" style="white-space: pre-wrap;">
              {{ para.text }}
            </v-list-item-subtitle>
            
            <div v-if="para.label === 'suspicious'" class="mt-3">
              <v-alert type="warning" variant="tonal" density="compact" class="text-body-2">
                <strong>可疑分析:</strong> {{ getExplanation(para.paragraph_index) || '该段落具有较高的 AI 生成特征。' }}
              </v-alert>
            </div>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import ResourceDetectionDetailStep from '@/components/steps/ResourceDetectionDetailStep.vue'

const props = defineProps<{
  task: any
  reviewerOptions: Array<{ id: number; username: string; avatar?: string | null }>
}>()

const emit = defineEmits<{
  (e: 'download'): void
  (e: 'request-review', payload: { reviewers: number[]; selected_file_ids: number[] }): void
}>()

const getExplanation = (index: number) => {
  const suspicious = props.task?.results?.suspicious_paragraphs || []
  const match = suspicious.find((s: any) => s.paragraph_index === index)
  return match ? match.explanation : ''
}
</script>
