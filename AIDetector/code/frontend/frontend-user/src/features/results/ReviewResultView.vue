<template>
  <div class="d-flex flex-column ga-4">
    <ResourceDetectionDetailStep :task="task" :reviewer-options="reviewerOptions" @download="emit('download')" @request-review="emit('request-review', $event)" />
    
    <!-- 评审内容段落检测结果展示 -->
    <v-card v-if="task?.results?.relevance_results?.length" class="mt-4" elevation="2" rounded="lg">
      <v-card-title class="d-flex align-center ga-2">
        <v-icon color="primary">mdi-file-compare</v-icon>
        <span class="text-h6">评审内容匹配与分析</span>
      </v-card-title>
      <v-card-text>
        <v-list lines="three">
          <v-list-item v-for="(para, index) in task.results.relevance_results" :key="index" class="mb-4 pa-4 bg-grey-lighten-4 rounded-lg">
            <template #prepend>
              <v-avatar :color="para.relevance_label === 'relevant' ? 'success' : 'error'" size="40" class="mr-4 text-white">
                {{ para.paragraph_index + 1 }}
              </v-avatar>
            </template>
            <v-list-item-title class="text-subtitle-1 font-weight-bold mb-2">
              分析结果: {{ para.relevance_label === 'relevant' ? '与论文内容相关' : '可能无关/存疑' }} 
              <v-chip size="small" :color="para.relevance_label === 'relevant' ? 'success' : 'error'" class="ml-2">
                相关度分数: {{ (para.relevance_score * 100).toFixed(1) }}%
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle class="text-body-1" style="white-space: pre-wrap;">
              <strong>Review 段落内容:</strong>
              {{ para.text }}
            </v-list-item-subtitle>
            
            <div class="mt-3">
              <v-alert type="info" variant="tonal" density="compact" class="text-body-2 mb-2">
                <strong>匹配的论文原段落 ({{ para.paper_paragraph_index + 1 }}):</strong><br>
                {{ para.paper_text }}
              </v-alert>
              <v-alert v-if="para.relevance_label !== 'relevant'" type="warning" variant="tonal" density="compact" class="text-body-2">
                <strong>分析解释:</strong> {{ para.relevance_explanation || '当前 Review 段落似乎未能找到与论文强相关的论述。' }}
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

defineProps<{
  task: any
  reviewerOptions: Array<{ id: number; username: string; avatar?: string | null }>
}>()

const emit = defineEmits<{
  (e: 'download'): void
  (e: 'request-review', payload: { reviewers: number[]; selected_file_ids: number[] }): void
}>()
</script>
